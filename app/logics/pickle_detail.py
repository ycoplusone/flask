from datetime import datetime

from sqlalchemy import text

from app import db


def normalize_ym(base_mm: str) -> str:
    """조회 년월: 숫자만 남김 (2026 / 202611 / 2026-11 → 2026 / 202611 / 202611), 없으면 올해"""
    digits = ''.join(ch for ch in (base_mm or '') if ch.isdigit())[:6]
    return digits or datetime.now().strftime('%Y')


def get_pickle_detail(base_mm: str, limit: int = 2000):
    """
    피클상세: 처리완료 기록(marco_detail) + 작업 정보(marco_info)
    조회 조건 : marco_detail.created_at 의 년월(YYYYMM) LIKE '입력값%'  (2026 → 2026년 전체, 202611 → 2026년 11월)
    반환 : (groups, total)  처리 기록 최대 limit 건을 작업(b.seq) 단위로 묶은 목록
           groups = [{seq, flag, job_nm, ..., t_cnt 성공 수, f_cnt 이상 수, last_at 최근 처리일시,
                      details: [{detail_seq, mi_seq, phone_number, status, etc, created_at}, ...]}, ...]
           작업 seq 최신 순 → mi_seq 순 → 처리 seq 순
    """
    base = """
        FROM marco_detail a
        JOIN marco_info b ON (a.mi_seq = b.seq)
        WHERE DATE_FORMAT(a.created_at, '%Y%m') LIKE :base_mm
    """
    params = {'base_mm': f'{base_mm}%'}

    total = db.session.execute(text("SELECT COUNT(*) " + base), params).scalar() or 0
    rows = db.session.execute(text("""
        SELECT b.seq
             , a.mi_seq
             , a.seq AS detail_seq   -- marco_detail 자체 키 (처리 기록 No)
             , a.phone_number        -- 처리한 전화번호
             , b.flag
             , b.job_nm
             , b.url
             , b.due_dt
             , b.ann_dt
             , b.event_nm
             , b.prize_nm
             , b.prize_cnt
             , a.etc
             , a.status
             , a.created_at
    """ + base + """
        ORDER BY 1 DESC, 2, a.seq
        LIMIT :limit
    """), {**params, 'limit': limit}).mappings().all()
    return _group_by_seq(rows), total


JOB_COLS = ('seq', 'flag', 'job_nm', 'url', 'due_dt', 'ann_dt', 'event_nm', 'prize_nm', 'prize_cnt')
DETAIL_COLS = ('detail_seq', 'mi_seq', 'phone_number', 'status', 'etc', 'created_at')


def _group_by_seq(rows):
    """조회 행(정렬 유지)을 작업 seq 단위로 묶음: 작업 정보 1번 + 처리 기록 목록"""
    groups, by_seq = [], {}
    for r in rows:
        g = by_seq.get(r['seq'])
        if g is None:
            g = {k: r[k] for k in JOB_COLS}
            g.update(details=[], t_cnt=0, f_cnt=0, last_at=None)
            by_seq[r['seq']] = g
            groups.append(g)
        g['details'].append({k: r[k] for k in DETAIL_COLS})
        if r['status'] == 'y':
            g['t_cnt'] += 1
        elif r['status'] == 'n':
            g['f_cnt'] += 1
        if r['created_at'] and (g['last_at'] is None or r['created_at'] > g['last_at']):
            g['last_at'] = r['created_at']
    return groups
