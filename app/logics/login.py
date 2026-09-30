from sqlalchemy import text

from app import db


def addDevice(user_id:str='',device_token:str='',user_agent:str='',expires_at='' ):
    '''새 기기 등록'''
    # user_agent는 브라우저 헤더에서 오는 외부 입력이므로 바인딩 파라미터로 전달
    sql = text("""
        INSERT INTO devDB.user_devices
        (user_id, device_token, user_agent, created_at, expires_at)
        VALUES(:user_id, :device_token, :user_agent, CURRENT_TIMESTAMP, :expires_at)
    """)
    db.session.execute(sql, {
        'user_id': user_id,
        'device_token': device_token,
        'user_agent': user_agent,
        'expires_at': expires_at,
    })
    db.session.commit()