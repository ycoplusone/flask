from flask import Blueprint, render_template

# 'main'이라는 이름의 블루프린트 생성
main_bp = Blueprint('main_bp', __name__)

@main_bp.route('/')
def home():
    # templates/index.html 파일을 찾아 화면을 그려줍니다 (렌더링)
    return render_template('test/app.html')

@main_bp.route('/test')
def test():
    # templates/index.html 파일을 찾아 화면을 그려줍니다 (렌더링)
    return render_template('test/app.html')