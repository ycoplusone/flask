from flask import Blueprint, render_template

from app.logics.temp_marco import get_temp_marco_list

temp_marco_bp = Blueprint('temp_marco_bp', __name__)


@temp_marco_bp.route('/temp_marco_info', methods=['GET'])
def temp_marco_list():
    """중복 등록 url 리스트 (temp_marco_info 조회 전용)"""
    rows, total = get_temp_marco_list()
    return render_template('marco/temp_marco_list.html', rows=rows, total=total)
