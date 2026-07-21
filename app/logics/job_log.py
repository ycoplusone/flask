from sqlalchemy import text

from app import db


def _sanitize(value: str) -> str:
    forbidden_chars = ["'", '"', "\\", ';', '%', '_', '`', '#', '-']
    for ch in forbidden_chars:
        value = value.replace(ch, '')
    return value


def macro_job_log(job_nm: str, url_path: str, flag: str):
    job_nm = _sanitize(job_nm)
    url_path = _sanitize(url_path)

    if flag == 'E':
        select_sql = text("""
            SELECT seq
            FROM marco_info
            WHERE url = :url_path
            ORDER BY seq DESC
            LIMIT 1
        """)
    else:
        select_sql = text("""
            SELECT seq
            FROM marco_info
            WHERE url = :url_path
              AND DATE_FORMAT(job_st_dt, '%Y%m%d') = DATE_FORMAT(NOW(), '%Y%m%d')
            ORDER BY seq DESC
            LIMIT 1
        """)

    result = db.session.execute(select_sql, {'url_path': url_path})
    row = result.fetchone()

    if not row:
        insert_sql = text(f"""
            INSERT INTO marco_info (job_nm, url, job_st_dt, job_ed_dt, job_st_cnt, job_ed_cnt)
            VALUES ('{job_nm}', '{url_path}', NOW(), NOW(), 1, 0)
        """)
        db.session.execute(insert_sql)
    else:
        seq = row[0]
        if flag == 'E':
            update_sql = text(f"""
                UPDATE marco_info
                SET job_ed_dt = NOW(), job_ed_cnt = job_ed_cnt + 1
                WHERE seq = '{seq}'
            """)
            db.session.execute(update_sql)
        else:
            update_sql = text("""
                UPDATE marco_info
                SET job_st_cnt = job_st_cnt + 1
                WHERE seq = :seq
            """)
            db.session.execute(update_sql, {'seq': seq})

    db.session.commit()
