import os
import base64
import mimetypes
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
    # REM 텍스트만 전송
    # curl -X POST http://localhost:5000/api/sms-receiver ^
    # -F "sender=01012345678" ^
    # -F "receiver=01087654321" ^
    # -F "message=안녕하세요" ^
    # -F "timestamp=2024-01-15T10:30:00"

    # REM 이미지 포함 전송 (MMS)
    # curl -X POST http://localhost:5000/api/sms-receiver ^
    # -F "sender=01012345678" ^
    # -F "receiver=01087654321" ^
    # -F "message=사진입니다" ^
    # -F "timestamp=2024-01-15T10:30:00" ^
    # -F "image=@C:\Users\DLIVE\Documents\cat.png"    
    
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


@main_bp.route('/api/textcatch', methods=['POST'])
def TextCatch():
    # REM SMS 전송 예시
    # curl -X POST http://localhost:5000/api/textcatch ^
    # -H "Content-Type: application/json" ^
    # -d "{\"type\":\"SMS\",\"sender\":\"01012345678\",\"receiver\":\"01099999999\",\"body\":\"Hello World\",\"timestamp\":1695123456789}"

    # REM MMS 전송 예시 (images 배열에 Base64 인코딩된 이미지 포함)
    # curl -X POST http://localhost:5000/api/textcatch ^
    # -H "Content-Type: application/json" ^
    # -d "{\"type\":\"MMS\",\"sender\":\"01012345678\",\"receiver\":\"01099999999\",\"body\":\"Check this image\",\"images\":[{\"mime_type\":\"image/jpeg\",\"data\":\"iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAIAAAACUFjqAAAAEklEQVR4nGP4z8CAB+GTG8HSALfKY52fTcuYAAAAAElFTkSuQmCC\"}],\"timestamp\":1695123456789}"

    # 1. JSON 파싱
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"status": "error", "message": "Invalid JSON body"}), 400

    # 2. 메타데이터 수신
    msg_type        = payload.get('type', 'SMS')        # SMS / MMS
    sender          = payload.get('sender')             # 발신자
    receiver        = payload.get('receiver')           # 수신자
    message_body    = payload.get('body', '')           # 메시지 내용
    timestamp       = payload.get('timestamp')          # 수신 시간 (epoch milliseconds)

    if not sender or not receiver:
        return jsonify({"status": "error", "message": "sender, receiver are required"}), 400

    # 3. timestamp(밀리초) -> datetime 문자열 변환 (없으면 현재 시간 사용)
    if timestamp:
        try:
            received_time = datetime.fromtimestamp(int(timestamp) / 1000).strftime('%Y-%m-%d %H:%M:%S')
        except (TypeError, ValueError):
            received_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    else:
        received_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 4. Base64 이미지 -> 파일 저장 (MMS의 경우, 이미지는 단일 파일)
    images = payload.get('images') or []
    image = images[0] if images else None

    image_filename = None
    b64_data = (image or {}).get('data')
    if b64_data:
        mime_type = image.get('mime_type', 'image/jpeg')
        ext = mimetypes.guess_extension(mime_type) or '.jpg'
        if ext == '.jpe':
            ext = '.jpg'

        # data URI 형식(data:image/jpeg;base64,....)으로 들어오는 경우 헤더 제거
        if b64_data.strip().startswith('data:') and ',' in b64_data:
            b64_data = b64_data.split(',', 1)[1]

        try:
            image_bytes = base64.b64decode(b64_data)

            # 파일명 중복 방지를 위해 타임스탬프와 발신번호 조합
            image_filename = secure_filename(f"{int(datetime.now().timestamp())}_{sender}{ext}")
            image_path = os.path.join(UPLOAD_FOLDER, image_filename)
            with open(image_path, 'wb') as f:
                f.write(image_bytes)
        except Exception as e:
            print(f"이미지 디코딩/저장 실패: {e}")
            image_filename = None

    # 5. 데이터 확인 (DB 적재는 추후 처리)
    print(f"[{received_time}] ({msg_type}) From: {sender} -> To: {receiver}")
    print(f"내용: {message_body}")
    if image_filename:
        print(f"첨부 이미지: {image_filename}")

    # TODO: DB 입력 처리
    setTextCatch(sender, receiver, message_body, received_time, image_filename)
    return jsonify({"status": "success", "message": "Data received successfully"}), 200
    