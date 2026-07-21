from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.logics.survey_words import (
    add_keyword,
    toggle_keyword,
    delete_keyword,
    get_search_keywords,
)

survey_words_bp = Blueprint('survey_words_bp', __name__)


@survey_words_bp.route('/survey_words', methods=['GET', 'POST'])
def survey_words():
    if request.method == 'POST':
        if request.form.get('action') == 'add':
            new_keyword = request.form.get('new_keyword', '').strip()
            if new_keyword:
                add_keyword(new_keyword)
                flash('키워드를 등록했습니다.', 'success')
        return redirect(url_for('survey_words_bp.survey_words'))

    toggle_id = request.args.get('toggle_id')
    delete_id = request.args.get('delete_id')
    if toggle_id:
        toggle_keyword(toggle_id)
        flash('키워드 사용 여부를 변경했습니다.', 'success')
        return redirect(url_for('survey_words_bp.survey_words'))

    if delete_id:
        delete_keyword(delete_id)
        flash('키워드를 삭제했습니다.', 'success')
        return redirect(url_for('survey_words_bp.survey_words'))

    keywords = get_search_keywords()
    return render_template('survey/survey_words.html', keywords=keywords)
