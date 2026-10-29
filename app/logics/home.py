from sqlalchemy import text
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
    upsert_received_info()
    sql = text("""
    select 
    case when COALESCE(min(c.hold_count + c.mms_unsent) over(partition by a.device_id),0) >= 1 then 9999999 else COALESCE(b.dd,0) end sort
    , a.device_id,a.receiver,tot_chk,sms_chk,mmm_chk
    , max(app_chk) over(partition by a.device_id) app_chk 
    , TIMESTAMPDIFF(hour, sms_dt, now()) sms_hour
    , TIMESTAMPDIFF(hour, mms_dt, now()) mms_hour
    , min(TIMESTAMPDIFF(hour, app_dt, now())) over(partition by a.device_id) app_hour
    , dely_tm
    , notes    
    , min(c.hold_count) over(partition by a.device_id) hold_count
    , min(c.mms_unsent) over(partition by a.device_id) mms_unsent
    , case when c.receiver is not null then 'T' else 'F' end pk_receiver
    from received_info a
    left outer join ( select device_id , max(case when tot_chk='F' then 9999999 else dely_tm end) dd from received_info where tot_chk = 'F'  or dely_tm >= 5    group by device_id ) b on (a.device_id  = b.device_id)
    left outer join received_app_info c on ( substr(a.receiver,-8) = substr(c.receiver,-8) )
    where a.receiver not in ('1234567890','+11002474588','01075126986','01099999999','+11081812350','+13111288616')
    order by 1 desc,2,3 ,4    
    """)
    result = db.session.execute(sql)
    return [dict(row) for row in result.mappings()]


def update_received_notes(device_id, receiver, notes) -> int:
    sql = text("""
    update received_info
    set notes = :notes
    where device_id = :device_id
      and receiver  = :receiver
    """)
    result = db.session.execute(sql, {'notes': notes, 'device_id': device_id, 'receiver': receiver})
    db.session.commit()
    return result.rowcount
