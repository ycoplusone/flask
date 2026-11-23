import re
from datetime import datetime

from sqlalchemy import text

from app import db
from app.logics.job_log import marco_url_lock, find_marco_seq


def sanitize_search_term(value: str) -> str:
    if not value:
        return '%'
    return re.sub(r"['""\\;%_`#-]", '', value)


def normalize_base_mm(base_mm: str) -> str:
    if not base_mm:
        return datetime.now().strftime('%Y')
    return base_mm


def get_survey_chart_data(base_mm: str):
    base_mm = normalize_base_mm(base_mm)
    params = {'base_mm': f'{base_mm}%'}
    
    # 시간별
    hour_sql = f"""
        SELECT DATE_FORMAT(job_st_dt, '%H시') AS h, 
        COUNT(DISTINCT CONCAT(job_nm, DATE_FORMAT(job_st_dt, '%Y%m%d'))) AS cnt 
        FROM marco_info 
        WHERE DATE_FORMAT(job_st_dt, '%Y%m%d') LIKE '{base_mm}%' 
        GROUP BY DATE_FORMAT(job_st_dt, '%H시') 
        ORDER BY 1 
    """
    hour_result = db.session.execute(text(hour_sql))
    sales_data = {'categories': [], 'series': [{'name': '개수', 'data': []}]}
    
    for row in hour_result.mappings():
        sales_data['categories'].append(row['h'])
        sales_data['series'][0]['data'].append(int(row['cnt']))    
    
    
    
    # 일별
    day_sql = f"""
         SELECT 
            DATE_FORMAT(job_st_dt, '%m/%d') AS d, 
            COUNT(DISTINCT CONCAT(job_nm, DATE_FORMAT(job_st_dt, '%Y%m%d'))) AS cnt 
         FROM marco_info 
         WHERE DATE_FORMAT(job_st_dt, '%Y%m%d') LIKE '{base_mm}%' 
         GROUP BY DATE_FORMAT(job_st_dt, '%m/%d') 
         ORDER BY 1
        """
    
    day_result = db.session.execute(text(day_sql))    
    expense_data = {'categories': [], 'series': [{'name': '개수', 'data': []}]}        
    for row in day_result.mappings():
        expense_data['categories'].append(row['d'])
        expense_data['series'][0]['data'].append(int(row['cnt']))



    # 월별
    month_sql = f"""
    SELECT 
        DATE_FORMAT(job_st_dt, '%m') AS d, 
        COUNT(DISTINCT CONCAT(job_nm, DATE_FORMAT(job_st_dt, '%Y%m%d'))) AS cnt 
    FROM marco_info 
    WHERE DATE_FORMAT(job_st_dt, '%Y') LIKE '{base_mm}%'
    GROUP BY DATE_FORMAT(job_st_dt, '%m') 
    ORDER BY DATE_FORMAT(job_st_dt, '%m') 
    """
    month_result = db.session.execute( text(month_sql) )
    months_data = {'categories': [], 'series': [{'name': '개수', 'data': []}]}
    for row in month_result.mappings():
        months_data['categories'].append(row['d'])
        months_data['series'][0]['data'].append(int(row['cnt']))

    return sales_data, expense_data, months_data


def get_survey_table_rows(base_mm: str, url: str):
    base_mm = normalize_base_mm(base_mm)
    url_search = sanitize_search_term(url)
    if url_search == '':
        url_search = '%'

    params = {
        'base_mm': f'{base_mm}%',
        'search_url': f'%{url_search}%'
    }

    table_sql = text(r"""
        SELECT 'Total' AS job_nm,
               '' AS url,
               '' AS flag,
               NULL AS sort,
               NULL AS due_dt, NULL AS ann_dt, NULL AS prize_nm, NULL AS prize_cnt, NULL AS etc,
               NOW() AS st_dt,
               '' AS ed_dt,
               SUM(job_st_cnt) AS st_ct,
               SUM(job_ed_cnt) AS ed_ct,
               COUNT(DISTINCT CONCAT(job_nm, DATE_FORMAT(job_st_dt, '%Y%m%d'))) AS tot_cnt , 
               '' t_cnt ,
                '' f_cnt ,
                0 sort_no
        FROM marco_info
        WHERE DATE_FORMAT(job_st_dt, '%Y%m%d') LIKE :base_mm
        UNION ALL
        SELECT a.job_nm,
            a.url,
            COALESCE(a.flag, 'human') AS flag,
            MAX(COALESCE(a.sort, 2)) AS sort,   -- 묶인 기록 중 큰 값 (수정하면 모두 같은 값이 됨)
            -- 아래 항목은 /survey_marco 가 새 행을 만들 때 저장. 묶인 기록 중 값이 있는 것(최대값) 표시
            MAX(NULLIF(a.due_dt, ''))    AS due_dt,     -- 마감일 YYYYMMDD
            MAX(NULLIF(a.ann_dt, ''))    AS ann_dt,     -- 발표일 YYYYMMDD
            MAX(NULLIF(a.prize_nm, ''))  AS prize_nm,   -- 상품
            MAX(NULLIF(a.prize_cnt, '')) AS prize_cnt,  -- 갯수
            MAX(NULLIF(a.etc, ''))       AS etc,        -- 기타(특이사항)
            MIN(a.job_st_dt) AS st_dt,
            MAX(a.job_ed_dt) AS ed_dt,
            SUM(a.job_st_cnt) AS st_ct,
            SUM(a.job_ed_cnt) AS ed_ct,
            COUNT(DISTINCT CONCAT(a.job_nm, DATE_FORMAT(a.job_st_dt, '%Y%m%d'))) AS tot_cnt ,
            sum(case when b.status = 'y'then 1 else 0 end) t_cnt,
            sum(case when b.status = 'n'then 1 else 0 end) f_cnt,
            case when max(COALESCE(a.due_dt, '')) = '' then 999 
            	when DATEDIFF(STR_TO_DATE(max(COALESCE(a.due_dt, '')), '%Y%m%d'), now()) <= -1 then 9999999
            	else  DATEDIFF(STR_TO_DATE(max(COALESCE(a.due_dt, '')), '%Y%m%d'), now())
            end sort_no            
        FROM marco_info a
        left outer join marco_detail b on (a.seq = b.mi_seq)
        WHERE DATE_FORMAT(a.job_st_dt, '%Y%m%d') LIKE :base_mm
        AND (COALESCE(a.url, '*') LIKE :search_url OR a.job_nm LIKE :search_url)
        GROUP BY a.job_nm, a.url, COALESCE(a.flag, 'human')
        ORDER BY 17
    """)

    result = db.session.execute(table_sql, params)
    return [dict(row) for row in result.mappings()]


MARCO_FLAGS = ('human', 'pickle', 'none')   # 화면 등록/수정에서 쓸 수 있는 구분 (ai 는 pickle 로 대체, none = 사용 안 함)


# 등록/수정 화면의 추가 항목 (모두 선택, 빈 값은 NULL)
MARCO_EXTRA_COLS = ('due_dt', 'ann_dt', 'prize_nm', 'prize_cnt', 'etc')


def _extraParams(extra: dict) -> dict:
    extra = extra or {}
    return {k: (extra.get(k) or None) for k in MARCO_EXTRA_COLS}


def add_marco_job(job_nm: str, url: str, flag: str, sort: int = 2, extra: dict = None) -> int:
    """
    작업 직접 등록 (marco_info 1행). 시작 시각은 지금, 시작/완료 횟수는 0
    - 같은 url 로 /job_log, /survey_marco 가 호출되면 날짜와 관계없이 이 행의 횟수가 올라감
    extra : {due_dt 마감일 YYYYMMDD, ann_dt 발표일 YYYYMMDD, prize_nm 상품, prize_cnt 갯수, etc 기타}
    반환 : 새 seq, url 이 이미 등록돼 있으면 None (url 중복 금지)
    """
    with marco_url_lock(url):
        if find_marco_seq(url):
            return None
        result = db.session.execute(text("""
            INSERT INTO marco_info (job_nm, url, flag, sort, due_dt, ann_dt, prize_nm, prize_cnt, etc,
                                    job_st_dt, job_ed_dt, job_st_cnt, job_ed_cnt)
            VALUES (:job_nm, :url, :flag, :sort, :due_dt, :ann_dt, :prize_nm, :prize_cnt, :etc,
                    NOW(), NULL, 0, 0)
        """), {'job_nm': job_nm, 'url': url, 'flag': flag, 'sort': sort, **_extraParams(extra)})
        db.session.commit()
        return result.lastrowid


def update_marco_job(org_job_nm: str, org_url: str, org_flag: str, job_nm: str, url: str, flag: str,
                     sort: int = 2, extra: dict = None) -> int:
    """
    작업 수정. 표의 한 행은 (작업명, url, flag) 로 묶인 기록이므로
    같은 (작업명, url, flag) 기록을 모두 함께 수정한다. (추가 항목도 같은 값으로 맞춤)
    반환 : 수정된 행 수, 바꾸려는 url 을 다른 작업이 이미 쓰고 있으면 -1 (url 중복 금지)
    """
    with marco_url_lock(url):
        if url != org_url and find_marco_seq(url):
            return -1
        result = db.session.execute(text("""
            UPDATE marco_info
            SET job_nm    = :job_nm
              , url       = :url
              , flag      = :flag
              , sort      = :sort
              , due_dt    = :due_dt
              , ann_dt    = :ann_dt
              , prize_nm  = :prize_nm
              , prize_cnt = :prize_cnt
              , etc       = :etc
            WHERE COALESCE(job_nm, '') = :org_job_nm   -- 표에는 NULL 이 빈 값으로 보이므로 동일하게 비교
              AND COALESCE(url, '')    = :org_url
              AND COALESCE(flag, 'human') = :org_flag
        """), {
            'job_nm': job_nm, 'url': url, 'flag': flag, 'sort': sort, **_extraParams(extra),
            'org_job_nm': org_job_nm, 'org_url': org_url, 'org_flag': org_flag,
        })
        db.session.commit()
        return result.rowcount
