from sqlalchemy import text
from app import db
import uuid # 고유 ID 생성을 위해 임포트

# 이 파일은 사용자 API와 관련된 순수한 비즈니스 로직을 담당합니다.
# 데이터베이스 조회, 계산 등의 핵심 로직이 여기에 위치합니다.

def dbtest():
    """
    데이터베이스 연결 테스트를 위한 비즈니스 로직.
    """
    print("✅ user_logic: dbtest() 호출됨 (Raw SQL 실행)")

    sql_query = text("SELECT 1")
    result = db.session.execute(sql_query)
    
    return {"status": "success", "result": [row._asdict() for row in result]}

def get_all_users():
    """
    Raw SQL을 실행하여 모든 사용자 데이터를 반환하는 비즈니스 로직.
    """
    print("✅ user_logic: get_all_users() 호출됨 (Raw SQL 실행)")

    sql_query = text("SELECT seq_id , dag_id , p_dag_id from dag_execution_logs ")

    result = db.session.execute(sql_query)
    
    # 결과를 [ {key: value}, ... ] 형태의 리스트로 변환
    users_list = [row._asdict() for row in result]
    
    return users_list

def add_new_user(user_data):
    """
    새로운 사용자를 Raw SQL(INSERT)을 사용하여 데이터베이스에 추가하는 비즈니스 로직.
    """
    print(f"✅ user_logic: add_new_user() 호출됨, 데이터: {user_data}")
    # 예시: username과 email을 받아서 저장
    username = user_data.get('username')
    email = user_data.get('email')
    
    sql_query = text("INSERT INTO users (username, email) VALUES (:username, :email)")
    db.session.execute(sql_query, {'username': username, 'email': email})
    db.session.commit() # 변경사항 커밋
    
    return {"id": str(uuid.uuid4()), "username": username, "email": email} # 임시 ID 반환