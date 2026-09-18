from sqlalchemy import text

from app import db

def setTextCatch(sender:str , receiver:str , message_body:str , received_time:str , image_filename:str = ''):
    """
    텍스트 수신 관련 설정을 초기화하는 함수.
    sender          = request.form.get('sender')    #수신자
    receiver        = request.form.get('receiver')   #발신자
    message_body    = request.form.get('message')   #메시지 내용
    received_time   = request.form.get('timestamp', datetime.now().isoformat()) #수신 시간 (없으면 현재 시간 사용)    
    """
    # 예시: 텍스트 수신 관련 설정을 DB에 저장
    sql_query = text(f"""
        INSERT INTO devDB.received_messages( sender, receiver, message_body, image_filename, received_at)
        VALUES( '{sender}', '{receiver}', '{message_body}', '{image_filename}', '{received_time}' );
    """)
    db.session.execute(sql_query)
    db.session.commit()

'''
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
'''