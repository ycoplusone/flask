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
