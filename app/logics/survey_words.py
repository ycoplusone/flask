from sqlalchemy import text

from app import db


def add_keyword(keyword: str):
    sql = text("""
        INSERT IGNORE INTO nicon_search_keywords (keyword, reg_dt)
        VALUES (:keyword, NOW())
    """)
    db.session.execute(sql, {'keyword': keyword})
    db.session.commit()


def toggle_keyword(keyword_id: str):
    sql = text("""
        UPDATE nicon_search_keywords
        SET is_use = IF(is_use = 'Y', 'N', 'Y')
        WHERE id = :keyword_id
    """)
    db.session.execute(sql, {'keyword_id': keyword_id})
    db.session.commit()


def delete_keyword(keyword_id: str):
    sql = text("""
        DELETE FROM nicon_search_keywords
        WHERE id = :keyword_id
    """)
    db.session.execute(sql, {'keyword_id': keyword_id})
    db.session.commit()


def get_search_keywords():
    sql = text("""
        SELECT *
        FROM nicon_search_keywords
        ORDER BY reg_dt DESC
    """)
    result = db.session.execute(sql)
    return [dict(row) for row in result.mappings()]
