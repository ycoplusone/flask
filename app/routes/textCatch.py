import os
import base64
import mimetypes
from flask import Blueprint, render_template,Flask, request, jsonify, send_from_directory, send_file, abort, flash, redirect, url_for
from app.logics.home import get_remaining_collection_count, get_last7_job_counts
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

from app.logics.textCatch import setTextCatch, getTextCatchList, deleteTextCatch, makeTextCatchExcel, makeTextCatchImageZip

# 'main'이라는 이름의 블루프린트 생성
main_bp = Blueprint('textCatch', __name__)

# 업로드 폴더는 git 저장소 바깥(프로젝트 루트의 상위 폴더)에 둡니다.
# CI/CD가 flask 폴더를 삭제 후 git에서 다시 받아도 수신 이미지가 유지됩니다.
# .env의 UPLOAD_FOLDER로 절대경로 지정 시 그 값을 우선 사용합니다. (예: /data/received_images)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))  # /home/dlive/flask
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(os.path.dirname(PROJECT_ROOT), 'received_images')
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
    message_body    = request.form.get('message', '')   #메시지 내용
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
    # image_filename이 None이면 f-string INSERT에서 문자열 'None'으로 저장되므로 빈 문자열로 전달
    setTextCatch(sender, receiver, message_body, received_time, image_filename or '')
    return jsonify({"status": "success", "message": "Data received successfully"}), 200


@main_bp.route('/textcatch', methods=['GET'])
def textCatchList():
    """수신 메시지 목록 화면 (기본 조회 조건: base_dt BETWEEN D-8 AND D-1)"""
    # 1. 검색 조건 수신 (없으면 기본값 D-8 ~ D-1)
    start_dt, end_dt, sender, keyword = _getSearchArgs()

    # 2. 목록 조회
    list_rows = getTextCatchList(start_dt, end_dt, sender, keyword)

    # 3. 화면 전달 (date input은 YYYY-MM-DD 형식이 필요하므로 변환값도 함께 전달)
    return render_template(
        'textcatch/textcatch_list.html',
        list_rows=list_rows,
        start_dt=start_dt,
        end_dt=end_dt,
        start_dt_view=f"{start_dt[0:4]}-{start_dt[4:6]}-{start_dt[6:8]}",
        end_dt_view=f"{end_dt[0:4]}-{end_dt[4:6]}-{end_dt[6:8]}",
        sender=sender,
        keyword=keyword,
    )


@main_bp.route('/textcatch/delete', methods=['POST'])
def textCatchDelete():
    """선택한 수신 메시지 삭제 (use_yn 'Y' -> 'N' 변경) 후 같은 조회 조건으로 목록 복귀"""
    ids = [int(v) for v in request.form.getlist('ids') if v.strip().isdigit()]

    if not ids:
        flash('삭제할 메시지를 선택해 주세요.', 'error')
    else:
        deleted = deleteTextCatch(ids)
        flash(f'{deleted}건을 삭제했습니다.', 'info')

    return redirect(url_for('textCatch.textCatchList',
                            start_dt=request.form.get('start_dt', ''),
                            end_dt=request.form.get('end_dt', ''),
                            sender=request.form.get('sender', ''),
                            keyword=request.form.get('keyword', '')))


@main_bp.route('/textcatch/image/<filename>')
def textCatchImage(filename):
    """업로드 폴더(저장소 바깥)에 저장된 수신 이미지를 화면에 보여주기 위한 서빙용 라우트"""
    safe_name = secure_filename(filename)
    if not safe_name:
        abort(404)
    return send_from_directory(UPLOAD_FOLDER, safe_name)


def _getSearchArgs():
    """목록/엑셀/이미지ZIP이 공통으로 쓰는 조회 조건 (기본 D-8 ~ D-1)"""
    today = datetime.now()
    default_start = (today - timedelta(days=8)).strftime('%Y%m%d')
    default_end = (today - timedelta(days=1)).strftime('%Y%m%d')

    start_dt = (request.args.get('start_dt') or default_start).replace('-', '').strip()
    end_dt = (request.args.get('end_dt') or default_end).replace('-', '').strip()
    sender = (request.args.get('sender') or '').strip()
    keyword = (request.args.get('keyword') or '').strip()

    # 시작일이 종료일보다 크면 서로 교환
    if start_dt > end_dt:
        start_dt, end_dt = end_dt, start_dt

    return start_dt, end_dt, sender, keyword


@main_bp.route('/textcatch/excel', methods=['GET'])
def textCatchExcel():
    """현재 조회 조건의 목록을 엑셀(xlsx)로 다운로드 (이미지 제외)"""
    start_dt, end_dt, sender, keyword = _getSearchArgs()

    list_rows = getTextCatchList(start_dt, end_dt, sender, keyword)
    excel_file = makeTextCatchExcel(list_rows)

    # 파일명: 조회기간 + 다운로드 시각
    download_name = f"수신메시지_{start_dt}_{end_dt}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"

    return send_file(
        excel_file,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=download_name,
    )


@main_bp.route('/textcatch/images', methods=['GET'])
def textCatchImageZip():
    """현재 조회 조건에 포함된 첨부 이미지를 ZIP으로 한번에 다운로드"""
    start_dt, end_dt, sender, keyword = _getSearchArgs()

    list_rows = getTextCatchList(start_dt, end_dt, sender, keyword)
    zip_file, file_count = makeTextCatchImageZip(list_rows, UPLOAD_FOLDER)

    # 받을 이미지가 없으면 빈 ZIP을 주지 않고 목록으로 돌려보냄
    if file_count == 0:
        flash('해당 기간에 다운로드할 이미지가 없습니다.', 'info')
        return redirect(url_for('textCatch.textCatchList',
                                start_dt=start_dt, end_dt=end_dt,
                                sender=sender, keyword=keyword))

    download_name = f"수신이미지_{start_dt}_{end_dt}_{datetime.now().strftime('%Y%m%d%H%M%S')}.zip"

    return send_file(
        zip_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=download_name,
    )
    

