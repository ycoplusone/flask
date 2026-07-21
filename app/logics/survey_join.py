import re
from datetime import datetime

from sqlalchemy import text

from app import db


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
               NOW() AS st_dt,
               '' AS ed_dt,
               SUM(job_st_cnt) AS st_ct,
               SUM(job_ed_cnt) AS ed_ct,
               COUNT(DISTINCT CONCAT(job_nm, DATE_FORMAT(job_st_dt, '%Y%m%d'))) AS tot_cnt
        FROM marco_info
        WHERE DATE_FORMAT(job_st_dt, '%Y%m%d') LIKE :base_mm
        UNION ALL
        SELECT job_nm,
               url,
               MIN(job_st_dt) AS st_dt,
               MAX(job_ed_dt) AS ed_dt,
               SUM(job_st_cnt) AS st_ct,
               SUM(job_ed_cnt) AS ed_ct,
               COUNT(DISTINCT CONCAT(job_nm, DATE_FORMAT(job_st_dt, '%Y%m%d'))) AS tot_cnt
        FROM marco_info
        WHERE DATE_FORMAT(job_st_dt, '%Y%m%d') LIKE :base_mm
          AND (COALESCE(url, '*') LIKE :search_url OR job_nm LIKE :search_url)
        GROUP BY job_nm, url
        ORDER BY 3 DESC
    """)

    result = db.session.execute(table_sql, params)
    return [dict(row) for row in result.mappings()]
