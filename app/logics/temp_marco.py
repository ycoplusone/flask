from sqlalchemy import text

from app import db


def get_temp_marco_list(limit: int = 1000):
    """
    중복 등록 url 리스트 (temp_marco_info)
    - /job_log, /survey_marco 에 flag = Z 로 이미 있는 url 이 들어온 기록
    반환 : (rows, total) 등록 시각(created_at) 최신 순, 최대 limit 건
    """
    total = db.session.execute(text("SELECT COUNT(*) FROM temp_marco_info")).scalar() or 0
    rows = db.session.execute(text("""
        SELECT a.seq
             , a.job_nm
             , a.url
             , a.flag
             , a.sort
             , a.due_dt
             , a.ann_dt
             , a.prize_nm
             , a.prize_cnt
             , a.event_nm
             , a.etc
             , a.created_at
        FROM temp_marco_info a
        ORDER BY a.created_at DESC, a.seq DESC
        LIMIT :limit
    """), {'limit': limit}).mappings().all()
    return rows, total
