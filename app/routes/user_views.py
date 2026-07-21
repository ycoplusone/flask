# /home/dlive/flask/app/views/user_views.py
from flask import Blueprint, render_template
from app.api import user_logic # user_logic 임포트

# 'user_views'라는 이름의 블루프린트 생성
user_views_bp = Blueprint('user_views', __name__, template_folder='../templates')

@user_views_bp.route('/users')
def user_list_page():
    """사용자 목록을 보여주는 HTML 페이지를 렌더링"""
    # user_logic에서 실제 사용자 데이터를 가져옵니다.
    users_data = user_logic.get_all_users()
    return render_template('test/list.html', users=users_data)