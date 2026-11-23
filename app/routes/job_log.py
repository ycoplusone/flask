from flask import Blueprint, request, jsonify

from app.logics.job_log import macro_job_log, normalize_due_dt, normalize_ymd

# /survey_marco 추가 텍스트 항목과 최대 길이 (marco_info 컬럼 길이)
SURVEY_MARCO_TEXT = {'prize_nm': 64, 'prize_cnt': 64, 'event_nm': 64, 'etc': 128}

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
    pickle 매크로 작업 기록 (marco_info.flag = 'pickle'). /job_log 와 동일하게 동작
    입력 : job_nm, url (form / query / JSON 모두 가능), flag (선택: 'E' 종료, 'Z' 중복 url 이면 temp_marco_info 에 등록, 없으면 시작)
           sort (선택: 정수, 없으면 2) → 새 행을 등록할 때 marco_info.sort 에 저장
           due_dt (선택: 마감일자 YYYYMMDD / YYYY-MM-DD) → 새 행을 등록할 때 YYYYMMDD 로 저장 (시간은 버림)
           ann_dt (선택: 발표일자, due_dt 와 같은 형식)
           prize_nm (선택: 상품, 64자) / prize_cnt (선택: 갯수, 64자) / event_nm (선택: 이벤트 종류, 64자) / etc (선택: 특이사항, 128자)
           ※ sort ~ etc 는 새 행을 만들 때만 저장 (같은 날 같은 url 재호출 시 기존 값 유지)
    예) curl -X POST http://localhost:5000/survey_marco -d "job_nm=설문A" -d "url=https://example.com/s?id=1"
    """
    data = request.get_json(silent=True) or {}
    job_nm = request.values.get('job_nm') or data.get('job_nm')
    url_path = request.values.get('url') or data.get('url')
    flag = request.values.get('flag') or data.get('flag') or 'z'
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

    due_raw = request.values.get('due_dt')
    if due_raw is None:
        due_raw = data.get('due_dt')
    due_dt, err = normalize_due_dt(due_raw)
    if err:
        return jsonify({'error': err}), 400

    def _get(name):
        v = request.values.get(name)
        return data.get(name) if v is None else v

    ann_dt, err = normalize_ymd(_get('ann_dt'), 'ann_dt')
    if err:
        return jsonify({'error': err}), 400

    extra = {'ann_dt': ann_dt}
    for name, max_len in SURVEY_MARCO_TEXT.items():
        v = _get(name)
        v = '' if v is None else str(v).strip()
        if len(v) > max_len:
            return jsonify({'error': f'{name} must be {max_len} characters or less'}), 400
        extra[name] = v or None

    macro_job_log(job_nm, url_path, flag, marco_flag='pickle', sort=sort, due_dt=due_dt, extra=extra)
    return jsonify({'status': 'ok'})
