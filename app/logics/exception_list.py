from sqlalchemy import text

from app import db


def add_exception_word(word: str):
    sql = text("""
        INSERT IGNORE INTO nicon_survey_exception_list (word, is_use)
        VALUES (:word, 'Y')
    """)
    db.session.execute(sql, {'word': word})
    db.session.commit()


def toggle_exception_word(word: str):
    sql = text("""
        UPDATE nicon_survey_exception_list
        SET is_use = IF(is_use = 'Y', 'N', 'Y')
        WHERE word = :word
    """)
    db.session.execute(sql, {'word': word})
    db.session.commit()


def delete_exception_word(word: str):
    sql = text("""
        DELETE FROM nicon_survey_exception_list
        WHERE word = :word
    """)
    db.session.execute(sql, {'word': word})
    db.session.commit()


def get_exception_words():
    sql = text("""
        SELECT *
        FROM nicon_survey_exception_list
        ORDER BY word ASC
    """)
    result = db.session.execute(sql)
    return [dict(row) for row in result.mappings()]
