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
