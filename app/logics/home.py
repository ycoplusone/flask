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
    group by base_dt
    order by base_dt desc
    """)
    result = db.session.execute(sql)
    return [dict(row) for row in result.mappings()]


def upsert_received_info():
    # raw string: MySQL 리터럴에 '^\\+8210' 그대로 전달
    sql = text(r"""
    INSERT INTO devDB.received_info(device_id, receiver, tot_chk, sms_chk, mmm_chk, sms_dt, mms_dt)
    select 
    device_id 
    , REGEXP_REPLACE(receiver, '^\\+8210', '010') as receiver 
    , case when sms_dt >= chk_tm or mms_dt >= chk_tm then 'T' else 'F' end tot_chk
    , case when sms_dt >= chk_tm then 'T' else 'F' end sms_chk
    , case when mms_dt >= chk_tm then 'T' else 'F' end mmm_chk
    , sms_dt
    , mms_dt
    from (
        select 
        device_id 
        , receiver	
        , max( case when COALESCE(image_filename, '')  = '' then created_at else STR_TO_DATE('1999-12-31 00:00:00', '%Y-%m-%d %H:%i:%s') end ) as sms_dt
        , max( case when COALESCE(image_filename, '') != '' then created_at else STR_TO_DATE('1999-12-31 00:00:00', '%Y-%m-%d %H:%i:%s') end ) as mms_dt
        , NOW() - INTERVAL 18 HOUR chk_tm
        from received_messages
        where base_dt between date_format( NOW() - INTERVAL 2 day , '%Y%m%d') and date_format( NOW() - INTERVAL 0 day , '%Y%m%d')
        and COALESCE(device_id,'') != ''
        group by device_id, receiver
    )  a
    ON DUPLICATE KEY UPDATE
        device_id = values(device_id),
        tot_chk = values(tot_chk) ,
        sms_chk = values(sms_chk) ,
        mmm_chk = values(mmm_chk) ,
        sms_dt = values(sms_dt) ,
        mms_dt = values(mms_dt) 
    """)
    db.session.execute(sql)
    db.session.commit()


def get_received_info():
    upsert_received_info()
    sql = text("""
    select 
    *
    from received_info
    order by 3,1,2
    """)
    result = db.session.execute(sql)
    return [dict(row) for row in result.mappings()]
