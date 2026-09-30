import os
from io import BytesIO

from sqlalchemy import text
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from PIL import Image as PILImage

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


def makeTextCatchExcel(list_rows: list, upload_folder: str):
    """
    수신 메시지 목록을 엑셀(xlsx)로 변환해 BytesIO로 반환.
    list_rows     : getTextCatchList() 결과
    upload_folder : 첨부 이미지가 저장된 폴더 (셀에 이미지를 직접 삽입하기 위해 사용)
    """
    wb = Workbook()
    ws = wb.active
    ws.title = '수신메시지'

    # 첨부 이미지는 원본 크기로 들어가므로 가장 오른쪽 컬럼에 배치
    headers = ['ID', '구분', '발신번호', '수신번호', '메시지 내용', '수신 시간', '기준일', '첨부 이미지']
    image_col = len(headers)          # 8 = H열
    image_col_letter = 'H'
    ws.append(headers)

    # 헤더 스타일
    header_fill = PatternFill('solid', fgColor='F2F2F2')
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = Font(bold=True)
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = Border(*[Side(style='thin', color='DDDDDD')] * 4)

    # 컬럼 너비 (H열은 이미지 원본 크기에 맞춰 뒤에서 다시 계산)
    for col, width in zip('ABCDEFG', [8, 8, 16, 18, 60, 20, 12]):
        ws.column_dimensions[col].width = width

    ws.freeze_panes = 'A2'

    # openpyxl은 저장 시점에 이미지 스트림을 읽으므로 참조를 유지해야 함
    image_buffers = []
    max_image_w = 0  # 삽입된 이미지 중 가장 큰 너비(px) - 컬럼 너비 계산용

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

        row_height = 18

        # 첨부 이미지를 원본 크기 그대로 삽입 (파일이 없으면 파일명만 텍스트로 표기)
        image_path = os.path.join(upload_folder, image_filename) if image_filename else ''
        if image_path and os.path.isfile(image_path):
            try:
                with PILImage.open(image_path) as im:
                    src_w, src_h = im.size
                    excel_format = os.path.splitext(image_filename)[1].lower() in ('.png', '.jpg', '.jpeg', '.gif')

                    if excel_format:
                        # 원본 파일을 그대로 삽입 (축소/재인코딩 없음)
                        xl_img = XLImage(image_path)
                    else:
                        # 엑셀이 지원하지 않는 포맷만 크기 유지한 채 PNG로 변환
                        if im.mode not in ('RGB', 'RGBA', 'L'):
                            im = im.convert('RGB')
                        buffer = BytesIO()
                        im.save(buffer, format='PNG')
                        buffer.seek(0)
                        image_buffers.append(buffer)
                        xl_img = XLImage(buffer)

                ws.add_image(xl_img, f'{image_col_letter}{idx}')

                # 원본 크기가 셀에 다 보이도록 행 높이 확보 (1px = 0.75pt)
                row_height = max(row_height, src_h * 0.75 + 4)
                max_image_w = max(max_image_w, src_w)
            except Exception as e:
                print(f"엑셀 이미지 삽입 실패({image_filename}): {e}")
                ws.cell(row=idx, column=image_col, value=image_filename)
        elif image_filename:
            ws.cell(row=idx, column=image_col, value=f"{image_filename} (파일 없음)")

        ws.row_dimensions[idx].height = row_height

    # 가장 큰 이미지가 다 보이도록 이미지 컬럼 너비 설정 (엑셀 너비 1 ≈ 7px)
    ws.column_dimensions[image_col_letter].width = max(16, max_image_w / 7 + 2)

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output
