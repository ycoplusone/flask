from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.logics.marco_phone import get_marco_by_phone, set_marco_done

marco_phone_bp = Blueprint('marco_phone_bp', __name__)


@marco_phone_bp.route('/marco_phone', methods=['GET'])
def marco_phone():
    """
    전화번호 기준 pickle 매크로 작업(marco_info.flag='pickle') 중 아직 안 한 작업 조회
    독립 화면 (상단 메뉴 없음, 메뉴 미등록)
    예) /marco_phone?phone=01012345678
    """
    phone = (request.args.get('phone') or '').strip()
    rows, total = get_marco_by_phone(phone)

    return render_template(
        'marco/marco_phone.html',
        phone=phone, rows=rows, total=total, searched=bool(phone),
    )


@marco_phone_bp.route('/marco_phone/done', methods=['POST'])
def marco_phone_done():
    """처리완료 버튼: marco_detail 에 기록 후 같은 전화번호로 목록 복귀"""
    phone = (request.form.get('phone') or '').strip()
    seq = request.form.get('seq', '')
    seq = int(seq) if seq.isdigit() else 0

    if set_marco_done(seq, phone):
        flash(f'{seq}번 작업을 처리완료했습니다.', 'info')
    else:
        flash('이미 처리완료됐거나 처리할 수 없는 작업입니다.', 'error')

    return redirect(url_for('marco_phone_bp.marco_phone', phone=phone))
