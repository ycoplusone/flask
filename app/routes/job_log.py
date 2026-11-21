from flask import Blueprint, request, jsonify

from app.logics.job_log import macro_job_log

job_log_bp = Blueprint('job_log_bp', __name__)


@job_log_bp.route('/job_log', methods=['POST'])
def job_log():
    job_nm = request.form.get('job_nm') or request.values.get('job_nm')
    flag = request.form.get('flag') or request.values.get('flag')
    url_path = request.form.get('url_path') or request.values.get('url_path')

    if not job_nm or not flag or not url_path:
        return jsonify({'error': 'job_nm, flag, url_path are required'}), 400

    macro_job_log(job_nm, url_path, flag)
    return jsonify({'status': 'ok'})


@job_log_bp.route('/survey_marco', methods=['POST'])
def survey_marco():
    """
    AI 매크로 작업 기록 (marco_info.flag = 'ai'). /job_log 와 동일하게 동작
    입력 : job_nm, url (form / query / JSON 모두 가능), flag (선택: 'E' 종료, 없으면 시작)
           sort (선택: 정수, 없으면 2) → 새 행을 등록할 때 marco_info.sort 에 저장
    예) curl -X POST http://localhost:5000/survey_marco -d "job_nm=설문A" -d "url=https://example.com/s?id=1"
    """
    data = request.get_json(silent=True) or {}
    job_nm = request.values.get('job_nm') or data.get('job_nm')
    url_path = request.values.get('url') or data.get('url')
    flag = request.values.get('flag') or data.get('flag') or 'S'
    sort_raw = request.values.get('sort')
    if sort_raw is None:
        sort_raw = data.get('sort')

    if not job_nm or not url_path:
        return jsonify({'error': 'job_nm, url are required'}), 400

    # sort 가 없거나 빈 값이면 2, 있으면 정수만 허용
    if sort_raw is None or str(sort_raw).strip() == '':
        sort = 2
    else:
        try:
            sort = int(str(sort_raw).strip())
        except ValueError:
            return jsonify({'error': 'sort must be an integer'}), 400

    macro_job_log(job_nm, url_path, flag, marco_flag='ai', sort=sort)
    return jsonify({'status': 'ok'})
