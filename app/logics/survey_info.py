from sqlalchemy import text

from app import db


def update_survey_url_verified(url: str):
    if not url:
        return

    sql = text("""
        UPDATE nicon_survey_collection
        SET is_verified = 1
        WHERE url = :url
    """)
    db.session.execute(sql, {'url': url})
    db.session.commit()


def update_survey_all_verified():
    sql = text("""
        UPDATE nicon_survey_collection
        SET is_verified = 1
        WHERE is_verified = 0
    """)
    db.session.execute(sql)
    db.session.commit()


def get_survey_table_rows(is_verified: str):
    params = {}
    where_clauses = ["collection_dt >= NOW() - INTERVAL 10 DAY"]

    if is_verified != 'all':
        where_clauses.append('is_verified = :is_verified')
        params['is_verified'] = 1 if is_verified == 'Y' else 0

    table_sql = text("""
        SELECT
            (has_qr * 4 + has_text_survey * 2 + has_text_satisfaction * 1)
            + (detail_qr * 4 + detail_txt * 2)
            + (CASE WHEN words IS NULL THEN 0 ELSE (CHAR_LENGTH(words) - CHAR_LENGTH(REPLACE(words, ',', ''))) + 1 END) AS sort_key,
            CASE WHEN words IS NULL THEN 0 ELSE (CHAR_LENGTH(words) - CHAR_LENGTH(REPLACE(words, ',', ''))) + 1 END AS word_cnt,
            has_qr * 4 + has_text_survey * 2 + has_text_satisfaction * 1 AS score,
            detail_qr * 4 + detail_txt * 2 AS ex_score,
            url,
            collection_dt,
            description,
            has_qr * 4 AS has_qr,
            has_text_survey * 2 AS has_text_survey,
            has_text_satisfaction * 1 AS has_text_satisfaction,
            detail_qr * 4 AS detail_qr,
            detail_txt * 2 AS detail_txt,
            is_verified,
            words
        FROM nicon_survey_collection
        WHERE """ + ' AND '.join(where_clauses) + """
        ORDER BY 1 DESC, 2 DESC, 3 DESC, collection_dt DESC
    """)

    result = db.session.execute(table_sql, params)
    return [dict(row) for row in result.mappings()]
