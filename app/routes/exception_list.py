from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.logics.exception_list import (
    add_exception_word,
    toggle_exception_word,
    delete_exception_word,
    get_exception_words,
)

exception_list_bp = Blueprint('exception_list_bp', __name__)


@exception_list_bp.route('/exception_list', methods=['GET', 'POST'])
def exception_list():
    if request.method == 'POST':
        new_word = request.form.get('new_word', '').strip()
        if new_word:
            add_exception_word(new_word)
            flash('제외 단어를 등록했습니다.', 'success')
        return redirect(url_for('exception_list_bp.exception_list'))

    toggle_word = request.args.get('toggle_word')
    delete_word = request.args.get('delete_word')

    if toggle_word:
        toggle_exception_word(toggle_word)
        flash('단어 사용 여부를 변경했습니다.', 'success')
        return redirect(url_for('exception_list_bp.exception_list'))

    if delete_word:
        delete_exception_word(delete_word)
        flash('제외 단어를 삭제했습니다.', 'success')
        return redirect(url_for('exception_list_bp.exception_list'))

    list_rows = get_exception_words()
    return render_template('survey/exception_list.html', list_rows=list_rows)
