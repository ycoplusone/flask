from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.logics.survey_join import (
    get_survey_chart_data, get_survey_table_rows, normalize_base_mm,
    add_marco_job, update_marco_job, MARCO_FLAGS,
)

survey_join = Blueprint('survey_join', __name__)


@survey_join.route('/survey_join', methods=['GET', 'POST'])
def survey_join1():
    base_mm = normalize_base_mm(request.values.get('base_mm', '').strip())
    url = request.values.get('url', '%')

    sales_data, expense_data, months_data = get_survey_chart_data(base_mm)
    table_rows = get_survey_table_rows(base_mm, url)

    return render_template(
        'survey/survey_join.html',
        base_mm=base_mm,
        url=url,
        sales_data=sales_data,
        expense_data=expense_data,
        months_data=months_data,
        table_rows=table_rows,
    )


def _readJobForm():
    """등록/수정 입력값 검사. 반환 (job_nm, url, flag, sort, 오류메시지) - sort 는 비우면 2"""
    job_nm = (request.form.get('job_nm') or '').strip()
    job_url = (request.form.get('job_url') or '').strip()
    flag = (request.form.get('flag') or '').strip()
    sort_raw = (request.form.get('sort') or '').strip()

    if not job_nm or not job_url:
        return None, None, None, None, '작업명과 URL을 입력해 주세요.'
    if len(job_nm) > 256:
        return None, None, None, None, '작업명: 256자 이하로 입력해 주세요.'
    if len(job_url) > 512:
        return None, None, None, None, 'URL: 512자 이하로 입력해 주세요.'
    if flag not in MARCO_FLAGS:
        return None, None, None, None, '구분은 human 또는 ai 만 가능합니다.'
    if sort_raw == '':
        sort = 2
    else:
        try:
            sort = int(sort_raw)
        except ValueError:
            return None, None, None, None, '정렬은 숫자로 입력해 주세요.'
    return job_nm, job_url, flag, sort, ''


def _redirectJoin():
    """등록/수정 후 같은 조회 조건으로 복귀"""
    return redirect(url_for('survey_join.survey_join1',
                            base_mm=request.form.get('base_mm', ''),
                            url=request.form.get('url') or '%'))


@survey_join.route('/survey_join/job/add', methods=['POST'])
def surveyJobAdd():
    job_nm, job_url, flag, sort, err = _readJobForm()
    if err:
        flash(err, 'error')
    else:
        seq = add_marco_job(job_nm, job_url, flag, sort)
        flash(f'작업을 등록했습니다. (No {seq}, {flag})', 'info')
    return _redirectJoin()


@survey_join.route('/survey_join/job/update', methods=['POST'])
def surveyJobUpdate():
    job_nm, job_url, flag, sort, err = _readJobForm()
    org_job_nm = request.form.get('org_job_nm')
    org_url = request.form.get('org_url')
    org_flag = request.form.get('org_flag') or 'human'

    if err:
        flash(err, 'error')
    elif org_job_nm is None or org_url is None:
        flash('수정할 행을 표에서 선택해 주세요.', 'error')
    else:
        cnt = update_marco_job(org_job_nm, org_url, org_flag, job_nm, job_url, flag, sort)
        if cnt:
            flash(f'{cnt}건을 수정했습니다.', 'info')
        else:
            flash('수정할 작업을 찾지 못했거나 바뀐 내용이 없습니다.', 'error')
    return _redirectJoin()
