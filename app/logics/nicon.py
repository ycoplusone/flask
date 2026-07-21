from sqlalchemy import text

from app import db


def get_nicon_sales_rows():
    query = """
    SELECT
        div_nm,
        brand,
        prod,
        fold_date,
        fold_cnt,
        bal_qty,
        suc_qty,
        chk_qty,
        DATE_FORMAT(c_date, '%Y/%m/%d') AS c_date,
        sale_qty
    FROM nicon_sale_list
    WHERE fold_cnt > 0
       OR bal_qty > 0
       OR suc_qty > 0
       OR chk_qty > 0
       OR sale_qty > 0
    ORDER BY SUBSTRING(fold_date, 1, 6), brand
    """

    result = db.session.execute(text(query))      
    print(text(query))
    r = [row._asdict() for row in result]
    return r
