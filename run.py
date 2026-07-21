from dotenv import load_dotenv

# .env 파일에서 환경 변수를 로드합니다. 이 코드는 다른 임포트보다 먼저 오는 것이 좋습니다.
load_dotenv() # 환경 변수는 여기서 한 번만 로드합니다.

from app import create_app

# app/__init__.py의 create_app 함수를 호출하여 Flask 앱을 생성합니다.
app = create_app() # noqa: E402

if __name__ == '__main__':
    # `python run.py`로 실행 시, 디버그 모드로 서버를 실행합니다.
    # 프로덕션 환경에서는 Gunicorn과 같은 WSGI 서버를 사용해야 합니다.
    app.run(host='0.0.0.0', port=5000)