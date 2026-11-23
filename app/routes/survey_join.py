from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.logics.job_log import normalize_ymd
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
        today=datetime.now().strftime('%Y%m%d'),   # 마감일 지남/오늘 표시용
    )


# 추가 텍스트 항목과 최대 길이 (marco_info 컬럼 길이)
EXTRA_TEXT = {'prize_nm': ('상품', 64), 'prize_cnt': ('갯수', 64), 'etc': ('기타', 128)}


def _readJobForm():
    """
    등록/수정 입력값 검사.
    반환 (job_nm, url, flag, sort, extra, 오류메시지)
      - sort 는 비우면 2
      - extra = {due_dt, ann_dt (YYYYMMDD), prize_nm, prize_cnt, etc}, 빈 값은 None
    """
    fail = lambda msg: (None, None, None, None, None, msg)
    job_nm = (request.form.get('job_nm') or '').strip()
    job_url = (request.form.get('job_url') or '').strip()
    flag = (request.form.get('flag') or '').strip()
    sort_raw = (request.form.get('sort') or '').strip()

    if not job_nm or not job_url:
        return fail('작업명과 URL을 입력해 주세요.')
    if len(job_nm) > 256:
        return fail('작업명: 256자 이하로 입력해 주세요.')
    if len(job_url) > 512:
        return fail('URL: 512자 이하로 입력해 주세요.')
    if flag not in MARCO_FLAGS:
        return fail('구분은 human, pickle, none 중 하나만 가능합니다.')
    if sort_raw == '':
        sort = 2
    else:
        try:
            sort = int(sort_raw)
        except ValueError:
            return fail('우선순위는 숫자로 입력해 주세요.')

    extra = {}
    for col, label in (('due_dt', '마감일'), ('ann_dt', '발표일')):
        value, err = normalize_ymd(request.form.get(col), col)   # 날짜 입력(YYYY-MM-DD) → YYYYMMDD
        if err:
            return fail(f'{label}: 올바른 날짜를 입력해 주세요.')
        extra[col] = value
    for col, (label, max_len) in EXTRA_TEXT.items():
        value = (request.form.get(col) or '').strip()
        if len(value) > max_len:
            return fail(f'{label}: {max_len}자 이하로 입력해 주세요.')
        extra[col] = value or None

    return job_nm, job_url, flag, sort, extra, ''


def _redirectJoin():
    """등록/수정 후 같은 조회 조건으로 복귀"""
    return redirect(url_for('survey_join.survey_join1',
                            base_mm=request.form.get('base_mm', ''),
                            url=request.form.get('url') or '%'))


@survey_join.route('/survey_join/job/add', methods=['POST'])
def surveyJobAdd():
    job_nm, job_url, flag, sort, extra, err = _readJobForm()
    if err:
        flash(err, 'error')
    else:
        seq = add_marco_job(job_nm, job_url, flag, sort, extra)
        if seq:
            flash(f'작업을 등록했습니다. (No {seq}, {flag})', 'info')
        else:
            flash('이미 등록된 URL 입니다. 표에서 해당 행을 선택해 수정해 주세요.', 'error')
    return _redirectJoin()


@survey_join.route('/survey_join/job/update', methods=['POST'])
def surveyJobUpdate():
    job_nm, job_url, flag, sort, extra, err = _readJobForm()
    org_job_nm = request.form.get('org_job_nm')
    org_url = request.form.get('org_url')
    org_flag = request.form.get('org_flag') or 'human'

    if err:
        flash(err, 'error')
    elif org_job_nm is None or org_url is None:
        flash('수정할 행을 표에서 선택해 주세요.', 'error')
    else:
        cnt = update_marco_job(org_job_nm, org_url, org_flag, job_nm, job_url, flag, sort, extra)
        if cnt == -1:
            flash('다른 작업이 이미 사용 중인 URL 입니다.', 'error')
        elif cnt:
            flash(f'{cnt}건을 수정했습니다.', 'info')
        else:
            flash('수정할 작업을 찾지 못했거나 바뀐 내용이 없습니다.', 'error')
    return _redirectJoin()
