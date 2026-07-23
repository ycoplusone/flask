from flask import Flask, render_template_string, request, redirect, url_for, make_response
import secrets
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os
import sys
from datetime import datetime, timedelta
from sqlalchemy import text

# 데이터베이스 객체 생성 (아직 앱과 연결되지 않음)
db = SQLAlchemy()



def create_app():
    app = Flask(__name__, instance_relative_config=True)
    CORS(app, supports_credentials=True)

    # ---------------------------------------------------------------------------
    # 3. Request 전처리 (기기 인증 검증)
    # ---------------------------------------------------------------------------
    @app.before_request
    def check_device_auth():
        # 로그인 페이지나 정적 파일(CSS 등) 접근 시에는 체크 건너뛰기
        if request.endpoint in ['loging_bp.login', 'static']:
            return

        # 브라우저 쿠키에서 device_token 가져오기
        token = request.cookies.get('device_token')

        if token:
            # MySQL DB에서 해당 토큰이 존재하고, 만료시간이 지나지 않았는지 확인
            sql = f"""
            SELECT *
            FROM user_devices
            WHERE device_token = '{token}'
            AND expires_at > NOW()
            LIMIT 1
            """

            result = db.session.execute(text(sql))
            device_record = [dict(row) for row in result.mappings()]

            # 유효한 기기 토큰이 DB에 있으면 통과 (자동 로그인 성립)
            if device_record:
                # (선택) g 객체 등에 로그인 사용자 정보를 보관할 수도 있습니다.
                return

        # 쿠키가 없거나 DB 인증에 실패하면 로그인 페이지로 리다이렉트
        return redirect('/login')

    
    @app.after_request
    def set_referrer_policy(response):
        response.headers["Referrer-Policy"] = 'no-referrer'
        return response  
    

    # config.py에서 설정을 로드합니다.
    app.config.from_object('config.DevelopmentConfig')
    # 개발 환경에서만 디버그 모드 활성화
    if app.config['DEBUG']:
        print(f"DEBUG mode is ON. Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}", file=sys.stderr)

    # 데이터베이스 객체와 앱 연결
    db.init_app(app)

    

    # api - start
    #from .apis.test import bp as test_api01_bp
    #app.register_blueprint(test_api01_bp, url_prefix='/api/test') # test  api 등록
    # api - end

    # routes - start
    from .routes.home import main_bp
    app.register_blueprint(main_bp) # test 화면

    from .routes.nicon import nicon_bp
    app.register_blueprint(nicon_bp) # nicon_bp 등록


    from .routes.survey_join import survey_join
    app.register_blueprint(survey_join) # survey_join 등록


    from .routes.survey_info import survey_info_bp
    app.register_blueprint(survey_info_bp) # survey_info_bp 등록

    from .routes.survey_words import survey_words_bp
    app.register_blueprint(survey_words_bp) # survey_words_bp 등록

    from .routes.target_words import target_words_bp
    app.register_blueprint(target_words_bp) # target_words_bp 등록

    from .routes.exception_list import exception_list_bp
    app.register_blueprint(exception_list_bp) # exception_list_bp 등록

    from .routes.job_log import job_log_bp
    app.register_blueprint(job_log_bp) # job_log_bp 등록


    from .routes.login import loging_bp
    app.register_blueprint(loging_bp) # 로그인 화면

    # routes - end


    return app