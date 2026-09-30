import os
import zipfile
from io import BytesIO

from sqlalchemy import text
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from app import db

def setTextCatch(sender:str , receiver:str , message_body:str , received_time:str , image_filename:str = ''):
    """
    텍스트 수신 관련 설정을 초기화하는 함수.
    sender          = request.form.get('sender')    #수신자
    receiver        = request.form.get('receiver')   #발신자
    message_body    = request.form.get('message')   #메시지 내용
    received_time   = request.form.get('timestamp', datetime.now().isoformat()) #수신 시간 (없으면 현재 시간 사용)    
    """
    # 값을 SQL에 직접 넣으면 메시지 내용의 작은따옴표(')에서 문법 오류가 나므로
    # 반드시 바인딩 파라미터로 전달한다.
    sql_query = text("""
        INSERT INTO devDB.received_messages( sender, receiver, message_body, image_filename, received_at)
        VALUES( :sender, :receiver, :message_body, :image_filename, :received_at )
    """)

    db.session.execute(sql_query, {
        'sender': sender,
        'receiver': receiver,
        'message_body': message_body,
        'image_filename': image_filename or '',
        'received_at': received_time,
    })
    db.session.commit()


def getTextCatchList(start_dt: str, end_dt: str, sender: str = '', keyword: str = ''):
    """
    수신 메시지(received_messages) 목록 조회.
    start_dt / end_dt : 조회 기준일(base_dt, varchar(8) YYYYMMDD) 범위
    sender            : 발신번호 부분검색 (선택)
    keyword           : 메시지 내용 부분검색 (선택)
    """
    sql = """
        SELECT id
             , sender
             , receiver
             , message_body
             -- 과거 데이터에 문자열 'None'이 들어간 건이 있어 빈 값으로 정규화
             , NULLIF(image_filename, 'None') AS image_filename
             , received_at
             , created_at
             , base_dt
        FROM received_messages
        WHERE base_dt BETWEEN :start_dt AND :end_dt        
    """
    params = {'start_dt': start_dt, 'end_dt': end_dt}

    if sender:
        sql += " AND sender LIKE :sender "
        params['sender'] = f"%{sender}%"

    if keyword:
        sql += " AND message_body LIKE :keyword "
        params['keyword'] = f"%{keyword}%"

    sql += " ORDER BY id DESC  "

    result = db.session.execute(text(sql), params)
    return [dict(row) for row in result.mappings()]


def makeTextCatchExcel(list_rows: list):
    """
    수신 메시지 목록을 엑셀(xlsx)로 변환해 BytesIO로 반환.
    이미지 컬럼은 제외한다. (이미지는 makeTextCatchImageZip으로 별도 다운로드)
    list_rows : getTextCatchList() 결과
    """
    wb = Workbook()
    ws = wb.active
    ws.title = '수신메시지'

    headers = ['ID', '구분', '발신번호', '수신번호', '메시지 내용', '수신 시간', '기준일']
    ws.append(headers)

    # 헤더 스타일
    header_fill = PatternFill('solid', fgColor='F2F2F2')
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = Font(bold=True)
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = Border(*[Side(style='thin', color='DDDDDD')] * 4)

    # 컬럼 너비
    for col, width in zip('ABCDEFG', [8, 8, 16, 18, 60, 20, 12]):
        ws.column_dimensions[col].width = width

    ws.freeze_panes = 'A2'

    for idx, row in enumerate(list_rows, start=2):
        image_filename = row.get('image_filename') or ''

        ws.cell(row=idx, column=1, value=row.get('id'))
        ws.cell(row=idx, column=2, value='MMS' if image_filename else 'SMS')
        ws.cell(row=idx, column=3, value=row.get('sender'))
        ws.cell(row=idx, column=4, value=row.get('receiver'))
        ws.cell(row=idx, column=5, value=row.get('message_body'))
        ws.cell(row=idx, column=6, value=str(row.get('received_at') or ''))
        ws.cell(row=idx, column=7, value=row.get('base_dt'))

        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=idx, column=col_idx)
            cell.alignment = Alignment(
                horizontal='left' if col_idx == 5 else 'center',
                vertical='center',
                wrap_text=(col_idx == 5),
            )

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def makeTextCatchImageZip(list_rows: list, upload_folder: str):
    """
    조회된 목록의 첨부 이미지를 ZIP으로 묶어 (BytesIO, 담긴 파일 수)로 반환.
    list_rows     : getTextCatchList() 결과
    upload_folder : 첨부 이미지가 저장된 폴더
    """
    output = BytesIO()
    added_names = set()
    file_count = 0

    # 이미지(jpg/png)는 이미 압축된 포맷이므로 다시 압축하지 않고 저장만 한다
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_STORED) as zf:
        for row in list_rows:
            image_filename = row.get('image_filename') or ''
            if not image_filename:
                continue

            image_path = os.path.join(upload_folder, image_filename)
            if not os.path.isfile(image_path):
                print(f"ZIP 대상 이미지 없음: {image_filename}")
                continue

            # 파일명이 겹치면 ID를 앞에 붙여 구분
            zip_name = image_filename
            if zip_name in added_names:
                zip_name = f"{row.get('id')}_{image_filename}"

            zf.write(image_path, zip_name)
            added_names.add(zip_name)
            file_count += 1

    output.seek(0)
    return output, file_count
