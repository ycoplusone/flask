from flask import Blueprint, render_template

from app.logics.nicon import get_nicon_sales_rows

# 'main'이라는 이름의 블루프린트 생성
nicon_bp = Blueprint('nicon_bp', __name__)


@nicon_bp.route('/nicon_sales')

def nicon_sales():
    try:
        rows = get_nicon_sales_rows()
        error_message = None
    except Exception as exc:
        rows = []
        error_message = f"데이터를 불러오지 못했습니다: {exc}"

    return render_template('nicon/nicon_sales.html', rows=rows, error_message=error_message)