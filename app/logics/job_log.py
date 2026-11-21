from datetime import datetime

from sqlalchemy import text

from app import db


def _sanitize(value: str) -> str:
    """
    job_nm / url 값의 정규화용.
    SQL 주입 방어는 바인딩 파라미터가 담당하므로 보안 목적은 아니며,
    기존에 저장된 marco_info.url 값과 동일한 형태로 맞춰 조회가 어긋나지 않게 하려고 유지한다.
    """
    forbidden_chars = ["'", '"', "\\", ';', '%', '_', '`', '#', '-']
    for ch in forbidden_chars:
        value = value.replace(ch, '')
    return value


def normalize_ymd(value, name: str = 'due_dt'):
    """
    날짜 입력값(마감일자 due_dt / 발표일자 ann_dt) → 'YYYYMMDD' (숫자 8자리, 시간은 저장하지 않음)
      허용 예) 20261130 / 2026-11-30 / 2026.11.30
              시간이 붙어 오면(2026-11-30 18:00, 202611301800, 20261130180000) 날짜만 사용
    반환 : (값 또는 None, 오류메시지)  빈 값이면 (None, '')
    """
    raw = '' if value is None else str(value).strip()
    if not raw:
        return None, ''
    digits = ''.join(ch for ch in raw if ch.isdigit())
    if len(digits) not in (8, 12, 14):
        return None, f'{name} must be YYYYMMDD'
    digits = digits[:8]
    try:
        datetime.strptime(digits, '%Y%m%d')   # 2026-02-30 같은 없는 날짜 거르기
    except ValueError:
        return None, f'{name} is not a valid date'
    return digits, ''


def normalize_due_dt(value):
    """마감일자(due_dt) → 'YYYYMMDD'"""
    return normalize_ymd(value, 'due_dt')


def macro_job_log(job_nm: str, url_path: str, flag: str, marco_flag: str = 'human', sort: int = 2, due_dt: str = None,
                  extra: dict = None):
    """
    매크로 작업 시작/종료 기록 (marco_info)
    flag       : 'E' 종료 기록, 그 외 시작 기록
    marco_flag : marco_info.flag 컬럼 값 ('human' 기본 / 'pickle' 은 /survey_marco API)
                 같은 url 이라도 flag 가 다르면 기록이 섞이지 않게 따로 집계
    sort       : marco_info.sort 값 (새 행을 만들 때만 저장, 기본 2)
    due_dt     : marco_info.due_dt 마감일자 'YYYYMMDD' (새 행을 만들 때만 저장, 없으면 NULL)
    extra      : 새 행을 만들 때만 저장하는 추가 항목 {ann_dt, prize_nm, prize_cnt, event_nm, etc} (없으면 NULL)
    """
    job_nm = _sanitize(job_nm)
    url_path = _sanitize(url_path)

    if flag == 'E':
        select_sql = text("""
            SELECT seq
            FROM marco_info
            WHERE url = :url_path
              AND COALESCE(flag, 'human') = :marco_flag
            ORDER BY seq DESC
            LIMIT 1
        """)
    else:
        select_sql = text("""
            SELECT seq
            FROM marco_info
            WHERE url = :url_path
              AND COALESCE(flag, 'human') = :marco_flag
              AND DATE_FORMAT(job_st_dt, '%Y%m%d') = DATE_FORMAT(NOW(), '%Y%m%d')
            ORDER BY seq DESC
            LIMIT 1
        """)

    result = db.session.execute(select_sql, {'url_path': url_path, 'marco_flag': marco_flag})
    row = result.fetchone()

    if not row:
        insert_sql = text("""
            INSERT INTO marco_info (job_nm, url, job_st_dt, job_ed_dt, job_st_cnt, job_ed_cnt, flag, sort, due_dt,
                                    ann_dt, prize_nm, prize_cnt, event_nm, etc)
            VALUES (:job_nm, :url_path, NOW(), NOW(), 1, 0, :marco_flag, :sort, :due_dt,
                    :ann_dt, :prize_nm, :prize_cnt, :event_nm, :etc)
        """)
        extra = extra or {}
        db.session.execute(insert_sql, {'job_nm': job_nm, 'url_path': url_path, 'marco_flag': marco_flag,
                                        'sort': sort, 'due_dt': due_dt,
                                        **{k: extra.get(k) for k in ('ann_dt', 'prize_nm', 'prize_cnt', 'event_nm', 'etc')}})
    else:
        seq = row[0]
        if flag == 'E':
            update_sql = text("""
                UPDATE marco_info
                SET job_ed_dt = NOW(), job_ed_cnt = job_ed_cnt + 1
                WHERE seq = :seq
            """)
            db.session.execute(update_sql, {'seq': seq})
        else:
            update_sql = text("""
                UPDATE marco_info
                SET job_st_cnt = job_st_cnt + 1
                WHERE seq = :seq
            """)
            db.session.execute(update_sql, {'seq': seq})

    db.session.commit()
