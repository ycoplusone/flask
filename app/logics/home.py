from sqlalchemy import bindparam, text
from app import db


def get_remaining_collection_count() -> int:
    sql = text("""
    SELECT count(1) cnt
    FROM nicon_survey_collection
    WHERE is_verified = 'N'
      AND collection_dt >= NOW() - INTERVAL 10 DAY
    """)
    result = db.session.execute(sql).scalar()
    return int(result or 0)


def get_last7_job_counts():
    sql = text("""
    SELECT 
        DATE_FORMAT(job_st_dt, '%m/%d') AS d, 
        COUNT(DISTINCT CONCAT(job_nm, DATE_FORMAT(job_st_dt, '%Y%m%d'))) AS cnt 
    FROM marco_info 
    WHERE job_st_dt >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
      AND job_st_dt <= NOW()
    GROUP BY DATE_FORMAT(job_st_dt, '%m/%d') 
    ORDER BY MIN(job_st_dt) desc
    """)
    result = db.session.execute(sql)
    return [dict(row) for row in result.mappings()]

def get_last7_text_counts():
    sql = text("""
    select 
    base_dt , count(distinct receiver) rec_cnt ,count(1) cnt
    from received_messages
    where base_dt between DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 7 DAY), '%Y%m%d') 
    and DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 0 DAY), '%Y%m%d')
    and use_yn = 'Y'
    AND COALESCE(SENDER, '') != ''
    group by base_dt
    order by base_dt desc
    """)
    result = db.session.execute(sql)
    return [dict(row) for row in result.mappings()]


def upsert_received_info():
    # 마지막 처리(created_dt) 후 1시간이 지나지 않았으면 skip (테이블이 비어있으면 NULL → 수행)
    chk_sql = text("""
    select min(created_dt) >= NOW() - INTERVAL 1 HOUR as is_recent
    from received_info
    """)
    if db.session.execute(chk_sql).scalar():
        return

    upd_sql = text("""
    update received_info
    set tot_chk = (case when sms_dt >= (NOW() - INTERVAL 12 HOUR) or mms_dt >= (NOW() - INTERVAL 12 HOUR) then 'T' else 'F' end)
    , sms_chk   = (case when sms_dt >= (NOW() - INTERVAL 12 HOUR) then 'T' else 'F' end)
    , mmm_chk   = (case when mms_dt >= (NOW() - INTERVAL 12 HOUR) then 'T' else 'F' end)
    , app_chk   = (case when app_dt >= (NOW() - INTERVAL 7 HOUR) then 'T' else 'F' end)
    , created_dt= now()
    """)
    db.session.execute(upd_sql)

    # raw string: MySQL 리터럴에 '^\\+8210' 그대로 전달
    sql = text(r"""
    INSERT INTO devDB.received_info(device_id, receiver, tot_chk, sms_chk, mmm_chk, sms_dt, mms_dt,dely_tm)
    select
        device_id , receiver 
        , case when max(sms_dt) >= max(chk_tm) or max(mms_dt) >= max(chk_tm) then 'T' else 'F' end tot_chk
        , case when max(sms_dt) >= max(chk_tm) then 'T' else 'F' end sms_chk
        , case when max(mms_dt) >= max(chk_tm) then 'T' else 'F' end mmm_chk
        , max(sms_dt) sms_dt
        , max(mms_dt) mms_dt
        , case when min(gubun) = 'a' then max(dely_tm_a) else max(dely_tm_b) end dely_tm
    from (
        select 
        device_id 
        , REGEXP_REPLACE(receiver, '^\\+8210', '010') as receiver	
        , max( case when COALESCE(image_filename, '')  = '' then created_at else STR_TO_DATE('1999-12-31 00:00:00', '%Y-%m-%d %H:%i:%s') end ) as sms_dt
        , max( case when COALESCE(image_filename, '') != '' then created_at else STR_TO_DATE('1999-12-31 00:00:00', '%Y-%m-%d %H:%i:%s') end ) as mms_dt
        , max(case when TIMESTAMPDIFF(MINUTE, received_at, created_at) > 5 then TIMESTAMPDIFF(MINUTE, received_at, created_at) else 0 end) as  dely_tm_a
        , 0 dely_tm_b
        , NOW() - INTERVAL 18 HOUR chk_tm
        , 'a' as gubun
        from received_messages
        where base_dt = date_format( NOW() - INTERVAL 0 day , '%Y%m%d') 
        and COALESCE(device_id,'') != ''
        AND COALESCE(SENDER, '') != ''  
        and use_yn = 'Y'
        and receiver not in ('+821075126986','1234567890','+11002474588','01099999999','+11081812350','+13111288616') #제외 전화번호
        group by device_id, REGEXP_REPLACE(receiver, '^\\+8210', '010')
        union all
        select
        device_id , receiver , sms_dt , mms_dt ,0 dely_tm_a, dely_tm dely_tm_b ,  NOW() - INTERVAL 18 HOUR chk_tm , 'b' as gubun
        from received_info        
        where receiver not in ('1234567890','+11002474588','01075126986','+821075126986','01099999999','+11081812350','+13111288616')
    ) a
    group by device_id , receiver 
        ON DUPLICATE KEY UPDATE
            device_id   = values(device_id),
            tot_chk     = values(tot_chk) ,
            sms_chk     = values(sms_chk) ,
            mmm_chk     = values(mmm_chk) ,
            sms_dt      = values(sms_dt)  ,
            mms_dt      = values(mms_dt)  ,
            dely_tm     = values(dely_tm)
    """)
    db.session.execute(sql)
    db.session.commit()


def get_received_info():
    '''
    정렬순서를
    16 : app 갱신 최근 3시간 초과 의 건
    8  : tot_chk 가 f인건
    4  : 미전송건이 발생
    2  : 지연이 발생건
    '''
    upsert_received_info()
    sql = text("""
    select 
    b.s0_tot 
    + b.s2_dely 
    + case when COALESCE(min(c.hold_count + c.mms_unsent) over(partition by a.device_id),0) > 0 then 4 else 0 end
    + case when min(TIMESTAMPDIFF(hour,c.updated_dt, now())) over(partition by a.device_id) > 3 then 16 else 0 end as sort
    , substr(a.device_id,1,5) as  device_id
    , a.receiver,tot_chk,sms_chk,mmm_chk
    , max(app_chk) over(partition by a.device_id) app_chk 
    , TIMESTAMPDIFF(hour, sms_dt, now()) sms_hour
    , TIMESTAMPDIFF(hour, mms_dt, now()) mms_hour
    , min(TIMESTAMPDIFF(hour, app_dt, now())) over(partition by a.device_id) app_hour
    , dely_tm
    , notes    
    , COALESCE(min(c.hold_count) over(partition by a.device_id),0) hold_count
    , COALESCE(min(c.mms_unsent) over(partition by a.device_id),0) mms_unsent
    , case when c.receiver is not null then 'T' else 'F' end pk_receiver
    , COALESCE(min(TIMESTAMPDIFF(hour,c.updated_dt, now())) over(partition by a.device_id),0) last_tm
    from received_info a
    left outer join ( 
    		select device_id 
    		, sum(case when tot_chk='F' then 8 else 0 end ) s0_tot
    		, max(case when dely_tm >= 5  then 2 else 0 end ) s2_dely
    		from received_info     
    		group by device_id     		) b on (a.device_id  = b.device_id)
    left outer join received_app_info c on ( substr(a.receiver,-8) = substr(c.receiver,-8) )
    where a.receiver not in ( select receiver from received_except ) # 제외 전화번호 등록 테이블
    order by 1 desc,2,3 ,4    
    """)
    result = db.session.execute(sql)
    return [dict(row) for row in result.mappings()]


def update_received_notes(receiver, notes) -> int:
    sql = text("""
    update received_info
    set notes = :notes
    where receiver  = :receiver
    """)
    result = db.session.execute(sql, {'notes': notes, 'receiver': receiver})
    db.session.commit()
    return result.rowcount


def update_gift_score() -> int:
    """
    최근 7일 수신 메시지의 기프티콘 점수(gift_score)를 계산해 더한다.
      대상 : received_messages 중 use_yn = 'Y' AND gift_yn = 'A' (미확인)
      1) message_body 에 received_gift_word.word(use_yn = 'Y') 가 포함된 단어 수만큼 +1 씩
      2) image_filename 이 있고 이미지에서 바코드가 검출되면 +500
      3) 더한 뒤 gift_score 가 3 이상이면 gift_yn = 'Y', 아니면 'N' (처리 완료 → 다음 실행 대상에서 제외)
    반환 : 처리(gift_yn 변경)된 건수

    필요 라이브러리 : opencv-python-headless (cv2.barcode.BarcodeDetector, OpenCV 4.8 이상)
    """
    import os
    # OpenCV 미설치 환경에서도 앱 기동(다른 화면)은 되도록 함수 안에서 import
    import cv2

    # 수신 이미지 폴더 (routes/textCatch.py 의 UPLOAD_FOLDER 와 동일한 규칙)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))  # /home/dlive/flask
    upload_folder = os.environ.get('UPLOAD_FOLDER') or os.path.join(os.path.dirname(project_root), 'received_images')

    # 1. 판별 단어 (사용 중인 것만, 대소문자 무시 비교를 위해 소문자로)
    word_rows = db.session.execute(text("""
        SELECT word
        FROM received_gift_word
        WHERE use_yn = 'Y'
    """)).scalars().all()
    words = [w.strip().lower() for w in word_rows if w and w.strip()]

    # 2. 대상 메시지 (최근 7일, 사용, 기프티콘 미확인)
    msg_rows = db.session.execute(text("""
        SELECT id
             , message_body
             -- 과거 데이터에 문자열 'None'이 들어간 건이 있어 빈 값으로 정규화
             , NULLIF(image_filename, 'None') AS image_filename
        FROM received_messages
        WHERE received_at >= NOW() - INTERVAL 7 DAY
          AND use_yn = 'Y'
          AND gift_yn = 'A'
    """)).mappings().all()

    # 바코드 검출기 설정 (기본값은 기프티콘 이미지에서 놓침·오검출이 많아 조정함)
    #   - 기본값(downsample 512, scales [0.01, 0.03, 0.06, 0.08]) : 최근 수신 이미지 기준 바코드 170건 중 125건 놓침, 오검출 4건
    #   - 아래 설정 : 170건 중 168건 검출, 오검출 0건
    #   setDownsamplingThreshold : 이미지를 이 크기(px) 이하로 줄여서 검사. 작을수록 큰 바코드를 잘 찾음
    #   setDetectorScales        : 검사 창 크기(이미지 대비 비율). 0.01(너무 작은 창)은 줄무늬 그림을 바코드로 오인해 제외
    detector = cv2.barcode.BarcodeDetector()
    detector.setDownsamplingThreshold(192)
    detector.setDetectorScales([0.03, 0.06, 0.08, 0.12])
    updates = []     # 이번에 점수가 생긴 건  : [{'id', 'score'}]
    zero_ids = []    # 이번에 점수가 0 인 건 : 점수 변화 없이 gift_yn 만 판단

    for row in msg_rows:
        score = 0

        # 2-1. 판별 단어 포함 개수만큼 +1
        body = (row['message_body'] or '').lower()
        score += sum(1 for w in words if w in body)

        # 2-2. 첨부 이미지에서 바코드 검출 시 +500
        image_filename = row['image_filename'] or ''
        if image_filename:
            image_path = os.path.join(upload_folder, image_filename)
            if os.path.isfile(image_path):
                try:
                    # 바코드 영역만 검출 (디코딩 성공 여부와 무관하게 위치가 잡히면 검출로 판단)
                    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        found, _points = detector.detect(img)
                        if found:
                            score += 500
                except Exception as e:
                    print(f"[update_gift_score] 바코드 검출 실패 id={row['id']} file={image_filename}: {e}")

        if score > 0:
            updates.append({'id': row['id'], 'score': score})
        else:
            zero_ids.append(row['id'])

    # 3. gift_score 에 더하고, 더한 점수가 3 이상이면 gift_yn = 'Y' / 아니면 'N'
    #    MySQL 은 SET 을 왼쪽부터 처리하며 앞에서 바뀐 값을 쓰므로
    #    gift_yn 을 먼저 (기존 점수 + 이번 점수) 로 판단한 뒤 gift_score 를 더한다.
    #    gift_yn = 'A' 조건은 그 사이 다른 실행이 먼저 처리한 건을 다시 더하지 않기 위함
    if updates:
        db.session.execute(text("""
            UPDATE received_messages
            SET gift_yn    = IF(COALESCE(gift_score, 0) + :score >= 3, 'Y', 'N')
              , gift_score = COALESCE(gift_score, 0) + :score
            WHERE id = :id
              AND gift_yn = 'A'
        """), updates)

    # 3-1. 점수 0 인 건은 한 번에 처리 (건별 UPDATE 는 원격 DB 왕복이 많아 느림, 1000건씩 나눠 실행)
    for i in range(0, len(zero_ids), 1000):
        db.session.execute(text("""
            UPDATE received_messages
            SET gift_yn = IF(COALESCE(gift_score, 0) >= 3, 'Y', 'N')
            WHERE id IN :ids
              AND gift_yn = 'A'
        """).bindparams(bindparam('ids', expanding=True)), {'ids': zero_ids[i:i + 1000]})

    if updates or zero_ids:
        db.session.commit()

    return len(updates) + len(zero_ids)
