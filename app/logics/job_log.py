import hashlib
from contextlib import contextmanager
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


@contextmanager
def marco_url_lock(url: str, timeout: int = 5):
    """
    marco_info.url 중복 방지용 잠금 (DB 유니크 인덱스 없이 프로그램에서 무결성 유지)
    - 같은 url 을 동시에 등록하려는 요청을 MySQL GET_LOCK 으로 한 줄로 세움
      → '조회 후 없으면 등록' 사이에 다른 요청이 끼어들어 같은 url 이 두 번 들어가는 것을 막음
    - 잠금은 별도 연결로 잡고, 안에서 commit 까지 끝낸 뒤 해제
    """
    name = 'marco_url:' + hashlib.md5((url or '').encode('utf-8')).hexdigest()   # 잠금 이름 최대 64자
    conn = db.engine.connect()
    try:
        conn.execute(text("SELECT GET_LOCK(:name, :timeout)"), {'name': name, 'timeout': timeout})
        yield
    finally:
        try:
            conn.execute(text("SELECT RELEASE_LOCK(:name)"), {'name': name})
        finally:
            conn.close()


def find_marco_seq(url: str):
    """url 이 같은 marco_info 행의 seq (예전 중복 행이 남아 있으면 가장 최근 것), 없으면 None"""
    return db.session.execute(text("""
        SELECT seq FROM marco_info WHERE url = :url ORDER BY seq DESC LIMIT 1
    """), {'url': url}).scalar()


def macro_job_log(job_nm: str, url_path: str, flag: str, marco_flag: str = 'human', sort: int = 2, due_dt: str = None,
                  extra: dict = None):
    """
    매크로 작업 시작/종료 기록 (marco_info)
    ※ url 중복 금지 (url 1개 = 1행) : 프로그램에서 보장 (marco_url_lock)
       - 같은 url 이 이미 있으면 날짜·flag 와 관계없이 그 행의 횟수만 올림 (새 행 만들지 않음)
       - 없으면 새 행 등록
    flag       : 'E' 종료 기록 (job_ed_dt 갱신, job_ed_cnt +1)
                 'Z' 같은 url 이 이미 있으면 marco_info 는 그대로 두고 temp_marco_info 에 1행 등록
                     (url 이 없으면 일반 시작 기록과 같이 marco_info 에 새 행 등록)
                 그 외 시작 기록 (job_st_cnt +1)
    marco_flag : 새 행을 만들 때 저장할 marco_info.flag ('human' 기본 / 'pickle' 은 /survey_marco API)
    sort       : marco_info.sort 값 (새 행을 만들 때만 저장, 기본 2)
    due_dt     : marco_info.due_dt 마감일자 'YYYYMMDD' (새 행을 만들 때만 저장, 없으면 NULL)
    extra      : 새 행을 만들 때만 저장하는 추가 항목 {ann_dt, prize_nm, prize_cnt, event_nm, etc} (없으면 NULL)
    """
    job_nm = _sanitize(job_nm)
    url_path = _sanitize(url_path)
    extra = extra or {}
    extra_params = {k: extra.get(k) for k in ('ann_dt', 'prize_nm', 'prize_cnt', 'event_nm', 'etc')}

    with marco_url_lock(url_path):
        seq = find_marco_seq(url_path)
        if seq and (flag or '').upper() == 'Z':
            # 중복 url + flag Z → temp_marco_info 에 보관 (marco_info 는 변경 없음)
            db.session.execute(text("""
                INSERT INTO temp_marco_info (job_nm, url, flag, sort, due_dt, ann_dt, prize_nm, prize_cnt, event_nm, etc)
                VALUES (:job_nm, :url_path, :marco_flag, :sort, :due_dt, :ann_dt, :prize_nm, :prize_cnt, :event_nm, :etc)
            """), {'job_nm': job_nm, 'url_path': url_path, 'marco_flag': marco_flag,
                   'sort': sort, 'due_dt': due_dt, **extra_params})
        elif seq:
            if flag == 'E':
                sql = "UPDATE marco_info SET job_ed_dt = NOW(), job_ed_cnt = job_ed_cnt + 1 WHERE seq = :seq"
            else:
                sql = "UPDATE marco_info SET job_st_cnt = job_st_cnt + 1 WHERE seq = :seq"
            db.session.execute(text(sql), {'seq': seq})
        else:
            db.session.execute(text("""
                INSERT INTO marco_info (job_nm, url, job_st_dt, job_ed_dt, job_st_cnt, job_ed_cnt, flag, sort, due_dt,
                                        ann_dt, prize_nm, prize_cnt, event_nm, etc)
                VALUES (:job_nm, :url_path, NOW(), NOW(), 1, 0, :marco_flag, :sort, :due_dt,
                        :ann_dt, :prize_nm, :prize_cnt, :event_nm, :etc)
            """), {'job_nm': job_nm, 'url_path': url_path, 'marco_flag': marco_flag,
                   'sort': sort, 'due_dt': due_dt, **extra_params})
        db.session.commit()
