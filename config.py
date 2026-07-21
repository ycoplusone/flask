# /home/dlive/flask/config.py

import os

class Config:
    """기본 설정"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-very-secret-key'
    # DATABASE_URL 환경 변수에서 직접 데이터베이스 URI를 읽어옵니다.
    # .env 파일에 DATABASE_URL이 정의되어 있어야 합니다.
    # 환경 변수가 없다면 기본값으로 SQLite를 사용하도록 설정할 수 있습니다.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
    # SQLAlchemy의 추가 메모리 사용을 방지하기 위해 False로 설정하는 것을 권장합니다.
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class DevelopmentConfig(Config):
    """개발 환경 설정"""
    DEBUG = True
    #HTML 템플릿이 수정되면 즉시 반영되도록 설정
    TEMPLATES_AUTO_RELOAD = True    