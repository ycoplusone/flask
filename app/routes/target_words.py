from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.logics.target_words import (
    add_target_word,
    toggle_target_word,
    delete_target_word,
    get_target_words,
)

target_words_bp = Blueprint('target_words_bp', __name__)


@target_words_bp.route('/target_words', methods=['GET', 'POST'])
def target_words():
    if request.method == 'POST':
        new_word = request.form.get('new_word', '').strip()
        if new_word:
            add_target_word(new_word)
            flash('단어를 추가했습니다.', 'success')
        return redirect(url_for('target_words_bp.target_words'))

    toggle_id = request.args.get('toggle_id')
    delete_id = request.args.get('delete_id')

    if toggle_id:
        toggle_target_word(toggle_id)
        flash('단어 사용 여부를 변경했습니다.', 'success')
        return redirect(url_for('target_words_bp.target_words'))

    if delete_id:
        delete_target_word(delete_id)
        flash('단어를 삭제했습니다.', 'success')
        return redirect(url_for('target_words_bp.target_words'))

    words = get_target_words()
    print(words)
    return render_template('survey/target_words.html', keywords=words)
