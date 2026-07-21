from flask import Blueprint,render_template_string, render_template, request, redirect, url_for, flash , make_response
import secrets
from datetime import datetime, timedelta

from app.logics.login import addDevice

loging_bp = Blueprint('loging_bp', __name__)


@loging_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # [A] 사용자 계정 검증 (예시)
        if username in ['우정','원일','봄'] and password == '1052':
            response = make_response(redirect('/'))
            
            # [B] 고유 기기 토큰 생성 및 만료일 지정 (예: 180일)
            token = secrets.token_hex(32)
            expire_days = 180
            expires_at = datetime.now() + timedelta(days=expire_days)
            user_agent_info = request.headers.get('User-Agent', '')[:255]

            # [C] MySQL DB에 기기 인증 정보 저장
            addDevice(user_id=username,
                      device_token=token,
                      user_agent=user_agent_info,
                      expires_at=expires_at
                    )            

            # [D] 브라우저에 Secure HTTP-Only 영속성 쿠키 발급
            response.set_cookie(
                'device_token',
                token,
                max_age=60 * 60 * 24 * expire_days, # 초 단위 (180일)
                httponly=True,                      # XSS 방지
                samesite='Lax'
            )
            return response
        else:
            return "아이디 또는 비밀번호가 올바르지 않습니다.", 400
    return render_template('login/app.html')

    