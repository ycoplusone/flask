from sqlalchemy import text

from app import db


def get_marco_by_phone(phone: str, limit: int = 500):
    """
    pickle 매크로 작업(marco_info.flag = 'pickle') 중 이 전화번호가 아직 하지 않은 작업 목록
      - 이미 한 작업 = marco_detail 에 (mi_seq, phone_number) 가 있는 작업 → 제외
    phone : 숫자만 남겨 비교 (010-1234-5678 → 01012345678)
    반환  : (rows, total) sort 낮은 순 → 최근 등록 순, 최대 limit 건
    """
    digits = ''.join(ch for ch in (phone or '') if ch.isdigit())
    if not digits:
        return [], 0

    base = """
        FROM marco_info a
        WHERE a.flag = 'pickle'
          AND a.seq NOT IN (
                SELECT mi_seq
                FROM marco_detail
                WHERE phone_number = :phone
          )
    """
    params = {'phone': digits}

    total = db.session.execute(text("SELECT COUNT(*) " + base), params).scalar() or 0

    rows = db.session.execute(text("""
        SELECT a.seq
             , a.job_nm
             , a.url
             , a.flag
             , a.job_st_dt AS created_at   -- marco_info 에 created_at 컬럼이 없어 등록 시각(job_st_dt) 사용
    """ + base + """
        ORDER BY COALESCE(a.sort, 2) ASC, a.seq DESC   -- sort 낮은 순, 같으면 최근 등록 순
        LIMIT :limit
    """), {**params, 'limit': limit}).mappings().all()

    return rows, total


def set_marco_done(seq: int, phone: str) -> bool:
    """
    처리완료: marco_detail 에 (mi_seq, phone_number) 기록 → 이후 이 번호 목록에서 제외
    - flag = 'pickle' 인 작업만 허용
    - 이미 기록된 건은 다시 넣지 않음 (버튼 연타/새로고침 대비)
    반환 : 새로 기록했으면 True
    """
    digits = ''.join(ch for ch in (phone or '') if ch.isdigit())
    if not digits or not seq:
        return False

    result = db.session.execute(text("""
        INSERT INTO marco_detail (mi_seq, phone_number, created_at)
        SELECT a.seq, :phone, NOW()
        FROM marco_info a
        WHERE a.seq = :seq
          AND a.flag = 'pickle'
          AND NOT EXISTS (
                SELECT 1
                FROM marco_detail d
                WHERE d.mi_seq = a.seq
                  AND d.phone_number = :phone
          )
    """), {'seq': seq, 'phone': digits})
    db.session.commit()
    return result.rowcount > 0
