# /home/dlive/flask/app/api/user_api.py
from flask import Blueprint, jsonify, request

import app.logics.test as test  # user_logic 임포트

# 'bp'라는 이름의 블루프린트 생성
bp = Blueprint('test_api01', __name__)

@bp.route('/dbtest', methods=['GET'])
def dbtest():
    """데이터베이스 연결 테스트를 위한 API (로직 계층 호출)"""    
    result = test.dbtest()  # 비즈니스 로직 호출
    return jsonify(result)

@bp.route('/users', methods=['GET'])
def get_users():
    """사용자 목록을 JSON 형태로 반환하는 API (로직 계층 호출)"""
    # 비즈니스 로직을 같은 폴더의 로직 파일에 위임합니다.
    users_data = test.get_all_users()
    return jsonify(users_data)

@bp.route('/users', methods=['POST'])
def create_user():
    """새로운 사용자를 생성하는 API (로직 계층 호출)"""
    data = request.json
    # 사용자 생성 로직을 같은 폴더의 로직 파일에 위임합니다.
    new_user = test.add_new_user(data)
    return jsonify({"message": "User created successfully", "user": new_user}), 201

@bp.route('/db-test')
def db_test():
    """데이터베이스 연결을 테스트하는 API"""
    from app import db # db 객체를 함수 내에서 임포트 (또는 전역으로 유지)
    try:
        # 간단한 쿼리를 실행하여 연결을 확인합니다.
        db.session.execute('SELECT 1')
        return jsonify({"status": "success", "message": "✅ Database connection successful!"})
    except Exception as e:
        # 에러 발생 시, 에러 메시지를 포함하여 응답합니다.
        db.session.rollback() # 에러 발생 시 롤백
        return jsonify({"status": "error", "message": f"❌ Database connection failed: {str(e)}"}), 500
    

@bp.route('/info')
def get_info():
    data = {
        "status": "success",
        "message": "구조화된 Flask 서버에서 보내는 데이터입니다.",
        "environment": "WSL (Ubuntu)"
    }
    return jsonify(data)