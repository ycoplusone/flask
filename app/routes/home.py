from flask import Blueprint, render_template, request, jsonify
from app.logics.home import get_remaining_collection_count, get_last7_job_counts, get_last7_text_counts, get_received_info, update_received_notes

# 'main'이라는 이름의 블루프린트 생성
main_bp = Blueprint('main_bp', __name__)


@main_bp.route('/')
def home():
    remaining_count = get_remaining_collection_count()
    week_counts = get_last7_job_counts()
    text_counts = get_last7_text_counts()
    received_info = get_received_info()
    return render_template('home/app.html', remaining_count=remaining_count, week_counts=week_counts, text_counts=text_counts, received_info=received_info)


@main_bp.route('/received-info')
def received_info():
    # 대시보드 SMS/MMS 수신 체크 영역 새로 고침용 (부분 HTML)
    return render_template('home/_received_info.html', received_info=get_received_info())


@main_bp.route('/received-info/notes', methods=['POST'])
def received_info_notes():
    # 대시보드 SMS/MMS 수신 체크 비고 저장
    data = request.get_json(silent=True) or {}
    device_id = data.get('device_id')
    receiver = data.get('receiver')
    if not device_id or not receiver:
        return jsonify({"status": "error", "message": "device_id, receiver are required"}), 400
    notes = (data.get('notes') or '').strip()
    cnt = update_received_notes(device_id, receiver, notes or None)
    if not cnt:
        return jsonify({"status": "error", "message": "대상 데이터가 없습니다."}), 404
    return jsonify({"status": "ok"})


@main_bp.route('/test')
def test():
    remaining_count = get_remaining_collection_count()
    week_counts = get_last7_job_counts()
    text_counts = get_last7_text_counts()
    received_info = get_received_info()
    return render_template('home/app.html', remaining_count=remaining_count, week_counts=week_counts, text_counts=text_counts, received_info=received_info)