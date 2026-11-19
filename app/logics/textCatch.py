import os
import json
import zipfile
from io import BytesIO
from sqlalchemy import bindparam, text
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from app import db

def setTextCatch( sender:str , receiver:str , message_body:str , received_time:str , device_id:str , sent_at:str ,attempt:str ,path:str,msg_id:str, image_filename:str = ''):
    """
    텍스트 수신 관련 설정을 초기화하는 함수.
    sender          = request.form.get('sender')    #수신자
    receiver        = request.form.get('receiver')   #발신자
    message_body    = request.form.get('message')   #메시지 내용
    device_id       = request.form.get('device_id')  #폰의 고유 ID (선택)
    received_time   = request.form.get('timestamp', datetime.now().isoformat()) #수신 시간 (없으면 현재 시간 사용)    
    """
    # 값을 SQL에 직접 넣으면 메시지 내용의 작은따옴표(')에서 문법 오류가 나므로
    # 반드시 바인딩 파라미터로 전달한다.
    sql_query = text("""
        INSERT INTO devDB.received_messages( sender, receiver, message_body, image_filename, received_at, device_id , sent_at , attempt , path,msg_id)
        VALUES( :sender, :receiver, :message_body, :image_filename, :received_at ,:device_id , :sent_at , :attempt , :path,:msg_id)
    """)

    db.session.execute(sql_query, {
        'sender': sender,
        'receiver': receiver or '1234567890',
        'message_body': message_body,
        'image_filename': image_filename or '',
        'received_at': received_time,
        'device_id': device_id or '',
        'sent_at': sent_at ,
        'attempt': attempt or '1',
        'path': path or '',
        'msg_id': msg_id or ''
    })


    # 이미지 없으면 SMS 컬럼만, 있으면 MMS 컬럼만 갱신 (반대쪽 값은 유지)
    if sender == '':
        upd_sql = text("""
        INSERT INTO devDB.received_info(device_id, receiver, app_chk , app_dt)
        values(:device_id, :receiver, 'T', now())
        ON DUPLICATE KEY UPDATE
        device_id   = values(device_id),
        app_chk     = values(app_chk) ,
        app_dt      = values(app_dt)
        """)
    elif image_filename:
        upd_sql = text("""
        INSERT INTO devDB.received_info(device_id, receiver, tot_chk,dely_tm, sms_chk, sms_dt,mmm_chk, mms_dt)
        values(:device_id, :receiver, 'T',0, 'F', STR_TO_DATE('1999-12-31 00:00:00', '%Y-%m-%d %H:%i:%s'), 'T', now())
        ON DUPLICATE KEY UPDATE
        device_id   = values(device_id),
        tot_chk     = values(tot_chk) ,
        mmm_chk     = values(mmm_chk) ,
        mms_dt      = values(mms_dt)   
        """)
    else:
        upd_sql = text("""
        INSERT INTO devDB.received_info(device_id, receiver, tot_chk,dely_tm, sms_chk, sms_dt,mmm_chk, mms_dt)
        values(:device_id, :receiver, 'T',0, 'T', now(), 'F', STR_TO_DATE('1999-12-31 00:00:00', '%Y-%m-%d %H:%i:%s'))
        ON DUPLICATE KEY UPDATE
        device_id   = values(device_id),
        tot_chk     = values(tot_chk) ,
        sms_chk     = values(sms_chk) ,
        sms_dt      = values(sms_dt) 
        """)
    if receiver.startswith("+8210"):
        receiver = "010" + receiver[5:]  # '+8210' 길이(5)만큼 자르고 '010' 결합

    db.session.execute(upd_sql, {'receiver': receiver or '1234567890', 'device_id': device_id or 'test'})
    db.session.commit()

def setAppLog( receiver , retry_count , inflight_count , hold_count , hold_oldest_received_time , hold_reasons , hold_dropped , corrupt_count , mms_unsent , mms_pending_download , mms_pending_oldest_time ):
    '''received_app_info 테이블에 HEARTBEAT 수신 시 상태를 기록한다. '''
    heartbeat_sql = text("""
            INSERT INTO devDB.received_app_info
            (receiver, retry_count, inflight_count, hold_count, hold_oldest_received_at, hold_reasons, hold_dropped, corrupt_count, mms_unsent, mms_pending_download, mms_pending_oldest)
            VALUES(:receiver, :retry_count, :inflight_count, :hold_count, :hold_oldest_received_at, :hold_reasons, :hold_dropped, :corrupt_count, :mms_unsent, :mms_pending_download, :mms_pending_oldest)
            ON DUPLICATE KEY UPDATE
                retry_count = VALUES(retry_count),
                inflight_count = VALUES(inflight_count),
                hold_count = VALUES(hold_count),
                hold_oldest_received_at = VALUES(hold_oldest_received_at),
                hold_reasons = VALUES(hold_reasons),
                hold_dropped = VALUES(hold_dropped),
                corrupt_count = VALUES(corrupt_count),
                mms_unsent = VALUES(mms_unsent),
                mms_pending_download = VALUES(mms_pending_download),
                mms_pending_oldest = VALUES(mms_pending_oldest),
                updated_dt = NOW()
        """)
    params = {
        'receiver': receiver or '1234567890',
        'retry_count': retry_count ,
        'inflight_count': inflight_count,
        'hold_count': hold_count , 
        'hold_oldest_received_at': hold_oldest_received_time,
        # dict는 바인딩 파라미터로 넘길 수 없으므로 JSON 문자열로 변환
        'hold_reasons': json.dumps(hold_reasons or {}) ,
        'hold_dropped': hold_dropped , 
        'corrupt_count': corrupt_count , 
        'mms_unsent': mms_unsent , 
        'mms_pending_download': mms_pending_download , 
        'mms_pending_oldest': mms_pending_oldest_time
    }

    # 디버그용: 바인딩 값이 채워진 실제 쿼리 출력
    try:
        db.session.execute(heartbeat_sql, params)
        db.session.commit()
    except Exception as e:
        print(f"[setAppLog] 쿼리 출력 실패: {e} / params={params}")





def getTextCatchList(start_dt: str, end_dt: str, sender: str = '', receiver: str = '', keyword: str = '', msg_type: str = '', gift_yn: str = '', use_yn: str = 'Y'):
    """
    수신 메시지(received_messages) 목록 조회.
    start_dt / end_dt : 조회 기준일(base_dt, varchar(8) YYYYMMDD) 범위
    sender            : 발신번호 부분검색 (선택)
    receiver          : 수신번호 부분검색 (선택)
    keyword           : 메시지 내용 또는 바코드 부분검색 (선택)
    msg_type          : 'MMS' 이미지 첨부 건 / 'SMS' 이미지 없는 건 / '' 전체 (선택)
    gift_yn           : 기프티콘여부 'A' 미확인 / 'N' 아님 / 'Y' 대상 / '' 전체 (선택)
    use_yn            : 상태 'Y' 사용 / 'N' 삭제 / 'A' 확인 / '' 전체 (기본 'Y')
    """
    sql = """
        SELECT a.id
             , a.sender
             , a.receiver
             , a.message_body
             -- 과거 데이터에 문자열 'None'이 들어간 건이 있어 빈 값으로 정규화
             , NULLIF(a.image_filename, 'None') AS image_filename
             , a.received_at
             , a.created_at
             , a.base_dt
             , TIMESTAMPDIFF(MINUTE, a.received_at, a.created_at) dely_tm
             , COALESCE(a.gift_yn, 'A') AS gift_yn
             , COALESCE(a.gift_score, 0) AS gift_score
             , REGEXP_SUBSTR(a.message_body, 'https?://[^ \t\r\n"''<>()]+') AS extracted_url
             , b.phone_numbers
             , COALESCE(a.use_yn, 'Y') AS use_yn
             , a.barcode
        FROM received_messages a
        left outer join (  -- 본회선/듀얼 전번호 출력
	        select substr( trim(z.receiver) ,-8) receiver , z.main_yn 
	        , (select group_concat( trim(receiver) order by main_yn desc SEPARATOR ','  ) from received_phone_list where z.group_id  = group_id  ) phone_numbers
	        from received_phone_list z
        ) b on ( substr(trim(a.receiver),-8) = b.receiver )
        WHERE a.base_dt BETWEEN :start_dt AND :end_dt
        AND COALESCE(a.SENDER, '') != ''
    """
    params = {'start_dt': start_dt, 'end_dt': end_dt}

    if sender:
        sql += " AND a.sender LIKE :sender "
        params['sender'] = f"%{sender}%"

    if receiver:
        sql += " AND a.receiver LIKE :receiver "
        params['receiver'] = f"%{receiver}%"

    if keyword:
        sql += " AND (a.message_body LIKE :keyword OR a.barcode LIKE :keyword) "
        params['keyword'] = f"%{keyword}%"

    # image_filename에 문자열 'None'이 들어간 과거 데이터도 SMS로 취급
    if msg_type == 'MMS':
        sql += " AND COALESCE(NULLIF(a.image_filename, 'None'), '') != '' "
    elif msg_type == 'SMS':
        sql += " AND COALESCE(NULLIF(a.image_filename, 'None'), '') = '' "

    if gift_yn in ('A', 'N', 'Y'):
        sql += " AND COALESCE(a.gift_yn, 'A') = :gift_yn "
        params['gift_yn'] = gift_yn

    if use_yn in ('A', 'N', 'Y'):
        sql += " AND COALESCE(a.use_yn, 'Y') = :use_yn "
        params['use_yn'] = use_yn

    sql += " ORDER BY id DESC  "

    result = db.session.execute(text(sql), params)
    return [dict(row) for row in result.mappings()]


def deleteTextCatch(ids: list) -> int:
    """
    수신 메시지 삭제 처리. 실제 DELETE 가 아니라 use_yn 을 'N' 으로 변경한다. (사용 Y / 확인 A 건 대상)
    ids : 삭제할 received_messages.id 목록
    반환 : 변경된 건수
    """
    if not ids:
        return 0

    sql = text("""
        UPDATE received_messages
        SET use_yn = 'N'
        WHERE id IN :ids
          AND COALESCE(use_yn, 'Y') != 'N'
    """).bindparams(bindparam('ids', expanding=True))

    result = db.session.execute(sql, {'ids': ids})
    db.session.commit()
    return result.rowcount


def confirmTextCatch(ids: list) -> int:
    """
    수신 메시지 확인 처리. 선택한 건의 use_yn 을 'A'(확인) 로 변경한다.
    ids : 확인 처리할 received_messages.id 목록
    반환 : 변경된 건수
    """
    if not ids:
        return 0

    sql = text("""
        UPDATE received_messages
        SET use_yn = 'A'
        WHERE id IN :ids
          AND COALESCE(use_yn, 'Y') != 'A'
    """).bindparams(bindparam('ids', expanding=True))

    result = db.session.execute(sql, {'ids': ids})
    db.session.commit()
    return result.rowcount


def updateTextCatchGiftYn(msg_id: int, gift_yn: str):
    """
    수신 메시지 대상(gift_yn) 수동 변경.
    gift_yn : 'Y' 대상 / 'N' 아님 / 'A' 미확인
              'A' 로 되돌리면 자동 판별(home.py)이 점수를 다시 더하므로 gift_score 를 0 으로 초기화
    반환 : 변경 후 {'gift_yn', 'gift_score'} / 대상 없으면 None
    """
    sql = text("""
        UPDATE received_messages
        SET gift_yn    = :gift_yn
          , gift_score = IF(:gift_yn = 'A', 0, gift_score)
        WHERE id = :id
    """)
    db.session.execute(sql, {'gift_yn': gift_yn, 'id': msg_id})
    db.session.commit()
    row = db.session.execute(text("""
        SELECT COALESCE(gift_yn, 'A') AS gift_yn, COALESCE(gift_score, 0) AS gift_score
        FROM received_messages
        WHERE id = :id
    """), {'id': msg_id}).mappings().first()
    return dict(row) if row else None


def updateTextCatchUseYn(msg_id: int, use_yn: str):
    """
    수신 메시지 상태(use_yn) 변경.
    use_yn : 'Y' 사용 / 'N' 삭제 / 'A' 확인
    반환 : 변경 후 use_yn / 대상 없으면 None
    """
    db.session.execute(
        text("UPDATE received_messages SET use_yn = :use_yn WHERE id = :id"),
        {'use_yn': use_yn, 'id': msg_id},
    )
    db.session.commit()
    return db.session.execute(
        text("SELECT COALESCE(use_yn, 'Y') FROM received_messages WHERE id = :id"),
        {'id': msg_id},
    ).scalar()


def makeTextCatchExcel(list_rows: list):
    """
    수신 메시지 목록을 엑셀(xlsx)로 변환해 BytesIO로 반환.
    이미지 컬럼은 제외한다. (이미지는 makeTextCatchImageZip으로 별도 다운로드)
    list_rows : getTextCatchList() 결과
    """
    wb = Workbook()
    ws = wb.active
    ws.title = '수신메시지'

    headers = ['ID', '구분', '발신번호', '수신번호', '메시지 내용', '수신 시간', '기준일', 'gift_yn(대상)', 'use_yn(상태)']
    ws.append(headers)

    # 헤더 스타일
    header_fill = PatternFill('solid', fgColor='F2F2F2')
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = Font(bold=True)
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = Border(*[Side(style='thin', color='DDDDDD')] * 4)

    # 컬럼 너비
    for col, width in zip('ABCDEFGHI', [8, 8, 16, 18, 60, 20, 12, 14, 14]):
        ws.column_dimensions[col].width = width

    ws.freeze_panes = 'A2'

    for idx, row in enumerate(list_rows, start=2):
        image_filename = row.get('image_filename') or ''

        ws.cell(row=idx, column=1, value=row.get('id'))
        ws.cell(row=idx, column=2, value='MMS' if image_filename else 'SMS')
        ws.cell(row=idx, column=3, value=row.get('sender'))
        ws.cell(row=idx, column=4, value=row.get('receiver'))
        ws.cell(row=idx, column=5, value=row.get('message_body'))
        ws.cell(row=idx, column=6, value=str(row.get('received_at') or ''))
        ws.cell(row=idx, column=7, value=row.get('base_dt'))
        ws.cell(row=idx, column=8, value=row.get('gift_yn'))
        ws.cell(row=idx, column=9, value=row.get('use_yn'))

        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=idx, column=col_idx)
            cell.alignment = Alignment(
                horizontal='left' if col_idx == 5 else 'center',
                vertical='center',
                wrap_text=(col_idx == 5),
            )

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def makeTextCatchImageZip(list_rows: list, upload_folder: str):
    """
    조회된 목록의 첨부 이미지를 ZIP으로 묶어 (BytesIO, 담긴 파일 수)로 반환.
    list_rows     : getTextCatchList() 결과
    upload_folder : 첨부 이미지가 저장된 폴더
    """
    output = BytesIO()
    added_names = set()
    file_count = 0

    # 이미지(jpg/png)는 이미 압축된 포맷이므로 다시 압축하지 않고 저장만 한다
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_STORED) as zf:
        for row in list_rows:
            image_filename = row.get('image_filename') or ''
            if not image_filename:
                continue

            image_path = os.path.join(upload_folder, image_filename)
            if not os.path.isfile(image_path):
                print(f"ZIP 대상 이미지 없음: {image_filename}")
                continue

            # 파일명이 겹치면 ID를 앞에 붙여 구분
            zip_name = image_filename
            if zip_name in added_names:
                zip_name = f"{row.get('id')}_{image_filename}"

            zf.write(image_path, zip_name)
            added_names.add(zip_name)
            file_count += 1

    output.seek(0)
    return output, file_count


# ------------------------------------------------------------------
# 기프티콘 여부 판별 단어 (received_gift_word) 관리
#   컬럼 : word(PK) / use_yn / score / created_dt
# ------------------------------------------------------------------
def getGiftWordList(keyword: str = ''):
    """기프티콘 판별 단어 목록 조회 (keyword: 단어 부분검색, 선택)"""
    sql = """
        SELECT word
             , use_yn
             , COALESCE(score, 1) AS score
             , created_dt
        FROM received_gift_word
    """
    params = {}
    if keyword:
        sql += " WHERE word LIKE :keyword "
        params['keyword'] = f"%{keyword}%"
    sql += " ORDER BY created_dt DESC, word "

    result = db.session.execute(text(sql), params)
    return [dict(row) for row in result.mappings()]


def addGiftWord(word: str, use_yn: str = 'Y', score: int = 1) -> bool:
    """
    기프티콘 판별 단어 등록.
    score  : 단어 포함 시 더할 점수 (음수면 감점)
    반환 : 등록되면 True, 이미 있는 단어(PK 중복)면 False
    """
    sql = text("""
        INSERT IGNORE INTO received_gift_word (word, use_yn, score, created_dt)
        VALUES (:word, :use_yn, :score, NOW())
    """)
    result = db.session.execute(sql, {'word': word, 'use_yn': use_yn, 'score': score})
    db.session.commit()
    return result.rowcount > 0


def updateGiftWord(org_word: str, word: str, use_yn: str, score: int = 1) -> str:
    """
    기프티콘 판별 단어 수정 (word 가 PK 이므로 원래 단어(org_word) 기준으로 갱신).
    반환 : 'ok' 수정 완료 / 'dup' 바꾸려는 단어가 이미 존재 / 'none' 대상 없음
    """
    if word != org_word:
        exists = db.session.execute(
            text("SELECT 1 FROM received_gift_word WHERE word = :word"),
            {'word': word},
        ).first()
        if exists:
            return 'dup'

    sql = text("""
        UPDATE received_gift_word
        SET word   = :word
          , use_yn = :use_yn
          , score  = :score
        WHERE word = :org_word
    """)
    result = db.session.execute(sql, {'word': word, 'use_yn': use_yn, 'score': score, 'org_word': org_word})
    db.session.commit()
    # 값이 그대로면 MySQL rowcount 가 0 일 수 있으므로 존재 여부로 판단
    if result.rowcount == 0:
        exists = db.session.execute(
            text("SELECT 1 FROM received_gift_word WHERE word = :word"),
            {'word': word},
        ).first()
        return 'ok' if exists else 'none'
    return 'ok'


def deleteGiftWord(words: list) -> int:
    """
    기프티콘 판별 단어 삭제 (실제 DELETE).
    words : 삭제할 단어 목록
    반환  : 삭제된 건수
    """
    if not words:
        return 0

    sql = text("""
        DELETE FROM received_gift_word
        WHERE word IN :words
    """).bindparams(bindparam('words', expanding=True))

    result = db.session.execute(sql, {'words': words})
    db.session.commit()
    return result.rowcount


# ------------------------------------------------------------------
# 수신 번호 (received_phone_list) 관리
#   컬럼 : receiver(PK) / group_id / main_yn / company / custom_no / pass_flag / notes / created_dt
#   group_id 가 같은 번호끼리 본회선(main_yn=Y) + 듀얼(N) 묶음
# ------------------------------------------------------------------
PHONE_COLS = ('group_id', 'receiver', 'main_yn', 'company', 'custom_no', 'pass_flag', 'notes')


def getPhoneList(keyword: str = '', company: str = ''):
    """
    수신 번호 목록 조회.
    keyword : 전화번호 / 그룹 / 사설구분번호 / 메모 부분검색 (선택)
    company : 통신사 일치 검색 (선택)
    """
    sql = """
        SELECT group_id, receiver, main_yn, company, custom_no, pass_flag, notes, created_dt
        FROM received_phone_list
        WHERE 1 = 1
    """
    params = {}
    if keyword:
        sql += """ AND ( receiver LIKE :keyword OR group_id = :keyword_eq OR custom_no LIKE :keyword
                         OR notes LIKE :keyword ) """
        params['keyword'] = f"%{keyword}%"
        params['keyword_eq'] = keyword
    if company:
        sql += " AND company = :company "
        params['company'] = company
    # 숫자 그룹은 숫자 순서로, 같은 그룹은 본회선(Y) 먼저
    sql += " ORDER BY CAST(group_id AS UNSIGNED), group_id, main_yn DESC, receiver "

    result = db.session.execute(text(sql), params)
    return [dict(row) for row in result.mappings()]


def getPhoneCodeList():
    """입력 보조용 통신사 / 패스 값 목록과 다음 그룹 번호"""
    companies = [r[0] for r in db.session.execute(text(
        "SELECT DISTINCT company FROM received_phone_list WHERE COALESCE(company, '') != '' ORDER BY company"))]
    pass_flags = [r[0] for r in db.session.execute(text(
        "SELECT DISTINCT pass_flag FROM received_phone_list WHERE COALESCE(pass_flag, '') != '' ORDER BY pass_flag"))]
    max_group = db.session.execute(text(
        "SELECT MAX(CAST(group_id AS UNSIGNED)) FROM received_phone_list")).scalar() or 0
    return companies, pass_flags, int(max_group) + 1


def _phoneExists(receiver: str) -> bool:
    return db.session.execute(
        text("SELECT 1 FROM received_phone_list WHERE receiver = :receiver"),
        {'receiver': receiver},
    ).first() is not None


def addPhone(data: dict) -> bool:
    """
    수신 번호 등록.
    반환 : 등록되면 True, 이미 있는 번호(PK 중복)면 False
    """
    sql = text("""
        INSERT IGNORE INTO received_phone_list
              (group_id, receiver, main_yn, company, custom_no, pass_flag, notes, created_dt)
        VALUES (:group_id, :receiver, :main_yn, :company, :custom_no, :pass_flag, :notes, NOW())
    """)
    result = db.session.execute(sql, {c: data.get(c) for c in PHONE_COLS})
    db.session.commit()
    return result.rowcount > 0


def updatePhone(org_receiver: str, data: dict) -> str:
    """
    수신 번호 수정 (receiver 가 PK 이므로 원래 번호(org_receiver) 기준으로 갱신).
    반환 : 'ok' 수정 완료 / 'dup' 바꾸려는 번호가 이미 존재 / 'none' 대상 없음
    """
    if data['receiver'] != org_receiver and _phoneExists(data['receiver']):
        return 'dup'

    sql = text("""
        UPDATE received_phone_list
        SET group_id  = :group_id
          , receiver  = :receiver
          , main_yn   = :main_yn
          , company   = :company
          , custom_no = :custom_no
          , pass_flag = :pass_flag
          , notes     = :notes
        WHERE receiver = :org_receiver
    """)
    params = {c: data.get(c) for c in PHONE_COLS}
    params['org_receiver'] = org_receiver
    result = db.session.execute(sql, params)
    db.session.commit()
    # 값이 그대로면 MySQL rowcount 가 0 일 수 있으므로 존재 여부로 판단
    if result.rowcount == 0:
        return 'ok' if _phoneExists(data['receiver']) else 'none'
    return 'ok'


def deletePhone(receivers: list) -> int:
    """수신 번호 삭제 (실제 DELETE). 반환 : 삭제된 건수"""
    if not receivers:
        return 0
    sql = text("""
        DELETE FROM received_phone_list
        WHERE receiver IN :receivers
    """).bindparams(bindparam('receivers', expanding=True))
    result = db.session.execute(sql, {'receivers': receivers})
    db.session.commit()
    return result.rowcount
