from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.logics.survey_info import (
    get_survey_table_rows,
    update_survey_url_verified,
    update_survey_all_verified,
)

survey_info_bp = Blueprint('survey_info_bp', __name__)


@survey_info_bp.route('/survey_info', methods=['GET', 'POST'])
@survey_info_bp.route('/survey_info/bare', methods=['GET', 'POST'], endpoint='survey_info_bare')
def survey_info():
    # /survey_info/bare : 상단 메뉴 없이 화면만 표시 (base_bare.html 사용)
    bare = request.endpoint == 'survey_info_bp.survey_info_bare'
    is_verified = request.values.get('is_verified', 'all')

    if request.method == 'POST':
        if request.form.get('update_url'):
            update_survey_url_verified(request.form['update_url'])
            flash('선택 항목을 완료 처리했습니다.', 'success')
        elif request.form.get('update_all'):
            update_survey_all_verified()
            flash('일괄 완료 처리가 완료되었습니다.', 'success')

        return redirect(url_for(request.endpoint, is_verified=is_verified))

    table_rows = get_survey_table_rows(is_verified)

    return render_template(
        'survey/survey_info.html',
        is_verified=is_verified,
        table_rows=table_rows,
        layout='base_bare.html' if bare else 'base.html',
    )
