from sqlalchemy import text

from app import db


def addDevice(user_id:str='',device_token:str='',user_agent:str='',expires_at='' ):
    '''새 기기 등록'''
    sql = text(f"""
        INSERT INTO devDB.user_devices
        (user_id, device_token, user_agent, created_at, expires_at)
        VALUES('{user_id}', '{device_token}', '{user_agent}', CURRENT_TIMESTAMP, '{expires_at}');
    """)
    db.session.execute(sql)
    db.session.commit()