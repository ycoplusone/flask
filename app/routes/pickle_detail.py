from flask import Blueprint, render_template, request

from app.logics.pickle_detail import get_pickle_detail, normalize_ym

pickle_detail_bp = Blueprint('pickle_detail_bp', __name__)


@pickle_detail_bp.route('/pickle_detail', methods=['GET'])
def pickle_detail():
    """피클상세: 처리완료 기록 조회 (조회 년월 like 검색, 예: /pickle_detail?base_mm=202611)"""
    base_mm = normalize_ym(request.args.get('base_mm'))
    groups, total = get_pickle_detail(base_mm)
    shown = sum(len(g['details']) for g in groups)
    return render_template('marco/pickle_detail.html', base_mm=base_mm, groups=groups, total=total, shown=shown)
