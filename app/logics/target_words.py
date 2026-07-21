from sqlalchemy import text

from app import db


def add_target_word(word: str):
    sql = text("""
        INSERT IGNORE INTO nicon_target_words (word)
        VALUES (:word)
    """)
    db.session.execute(sql, {'word': word})
    db.session.commit()


def toggle_target_word(word_id: str):
    sql = text("""
        UPDATE nicon_target_words
        SET is_use = IF(is_use = 'Y', 'N', 'Y')
        WHERE id = :word_id
    """)
    db.session.execute(sql, {'word_id': word_id})
    db.session.commit()


def delete_target_word(word_id: str):
    sql = text("""
        DELETE FROM nicon_target_words
        WHERE id = :word_id
    """)
    db.session.execute(sql, {'word_id': word_id})
    db.session.commit()


def get_target_words():
    sql = text("""
        SELECT *
        FROM nicon_target_words
        ORDER BY reg_dt DESC
    """)
    result = db.session.execute(sql)
    return [dict(row) for row in result.mappings()]
