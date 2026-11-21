from sqlalchemy import text

from app import db


def _sanitize(value: str) -> str:
    """
    job_nm / url 값의 정규화용.
    SQL 주입 방어는 바인딩 파라미터가 담당하므로 보안 목적은 아니며,
    기존에 저장된 marco_info.url 값과 동일한 형태로 맞춰 조회가 어긋나지 않게 하려고 유지한다.
    """
    forbidden_chars = ["'", '"', "\\", ';', '%', '_', '`', '#', '-']
    for ch in forbidden_chars:
        value = value.replace(ch, '')
    return value


def macro_job_log(job_nm: str, url_path: str, flag: str, marco_flag: str = 'human'):
    """
    매크로 작업 시작/종료 기록 (marco_info)
    flag       : 'E' 종료 기록, 그 외 시작 기록
    marco_flag : marco_info.flag 컬럼 값 ('human' 기본 / 'ai' 는 /survey_marco API)
                 같은 url 이라도 human / ai 기록은 서로 섞이지 않게 따로 집계
    """
    job_nm = _sanitize(job_nm)
    url_path = _sanitize(url_path)

    if flag == 'E':
        select_sql = text("""
            SELECT seq
            FROM marco_info
            WHERE url = :url_path
              AND COALESCE(flag, 'human') = :marco_flag
            ORDER BY seq DESC
            LIMIT 1
        """)
    else:
        select_sql = text("""
            SELECT seq
            FROM marco_info
            WHERE url = :url_path
              AND COALESCE(flag, 'human') = :marco_flag
              AND DATE_FORMAT(job_st_dt, '%Y%m%d') = DATE_FORMAT(NOW(), '%Y%m%d')
            ORDER BY seq DESC
            LIMIT 1
        """)

    result = db.session.execute(select_sql, {'url_path': url_path, 'marco_flag': marco_flag})
    row = result.fetchone()

    if not row:
        insert_sql = text("""
            INSERT INTO marco_info (job_nm, url, job_st_dt, job_ed_dt, job_st_cnt, job_ed_cnt, flag)
            VALUES (:job_nm, :url_path, NOW(), NOW(), 1, 0, :marco_flag)
        """)
        db.session.execute(insert_sql, {'job_nm': job_nm, 'url_path': url_path, 'marco_flag': marco_flag})
    else:
        seq = row[0]
        if flag == 'E':
            update_sql = text("""
                UPDATE marco_info
                SET job_ed_dt = NOW(), job_ed_cnt = job_ed_cnt + 1
                WHERE seq = :seq
            """)
            db.session.execute(update_sql, {'seq': seq})
        else:
            update_sql = text("""
                UPDATE marco_info
                SET job_st_cnt = job_st_cnt + 1
                WHERE seq = :seq
            """)
            db.session.execute(update_sql, {'seq': seq})

    db.session.commit()
