import os
from flask import Blueprint, render_template,Flask, request, jsonify
from app.logics.home import get_remaining_collection_count, get_last7_job_counts
from werkzeug.utils import secure_filename
from datetime import datetime

from app.logics.textCatch import setTextCatch

# 'main'이라는 이름의 블루프린트 생성
main_bp = Blueprint('textCatch', __name__)

UPLOAD_FOLDER = './received_images'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@main_bp.route('/api/sms-receiver', methods=['POST'])
def receive_message():
# 1. 텍스트 메타데이터 수신
    sender          = request.form.get('sender')    #수신자
    receiver        = request.form.get('receiver')   #발신자
    message_body    = request.form.get('message')   #메시지 내용
    received_time   = request.form.get('timestamp', datetime.now().isoformat()) #수신 시간 (없으면 현재 시간 사용)
    
    # 2. 이미지 파일 처리 (MMS의 경우)
    image_filename = None
    if 'image' in request.files:
        image_file = request.files['image']
        if image_file.filename != '':
            ext = os.path.splitext(image_file.filename)[1]
            # 파일명 중복 방지를 위해 타임스탬프와 발신번호 조합
            image_filename = secure_filename(f"{int(datetime.now().timestamp())}_{sender}{ext}")
            image_path = os.path.join(UPLOAD_FOLDER, image_filename)
            image_file.save(image_path)

    # 3. 데이터 검증 및 저장 (DB 적재 등)
    print(f"[{received_time}] From: {sender} -> To: {receiver}")
    print(f"내용: {message_body}")
    if image_filename:
        print(f"첨부 이미지: {image_filename}")
        setTextCatch(sender, receiver, message_body, received_time, image_filename)
    else:
        setTextCatch(sender, receiver, message_body, received_time)

    return jsonify({"status": "success", "message": "Data received successfully"}), 200

