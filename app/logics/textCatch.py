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


def getTextCatchList(start_dt: str, end_dt: str, sender: str = '', keyword: str = ''):
    """
    수신 메시지(received_messages) 목록 조회.
    start_dt / end_dt : 조회 기준일(base_dt, varchar(8) YYYYMMDD) 범위
    sender            : 발신번호 부분검색 (선택)
    keyword           : 메시지 내용 부분검색 (선택)
    """
    sql = """
        SELECT id
             , sender
             , receiver
             , message_body
             -- 과거 데이터에 문자열 'None'이 들어간 건이 있어 빈 값으로 정규화
             , NULLIF(image_filename, 'None') AS image_filename
             , received_at
             , created_at
             , base_dt
        FROM received_messages
        WHERE base_dt BETWEEN :start_dt AND :end_dt        
    """
    params = {'start_dt': start_dt, 'end_dt': end_dt}

    if sender:
        sql += " AND sender LIKE :sender "
        params['sender'] = f"%{sender}%"

    if keyword:
        sql += " AND message_body LIKE :keyword "
        params['keyword'] = f"%{keyword}%"

    sql += " ORDER BY id DESC  "

    result = db.session.execute(text(sql), params)
    return [dict(row) for row in result.mappings()]
