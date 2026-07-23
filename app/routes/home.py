from flask import Blueprint, render_template
from app.logics.home import get_remaining_collection_count, get_last7_job_counts

# 'main'이라는 이름의 블루프린트 생성
main_bp = Blueprint('main_bp', __name__)


@main_bp.route('/')
def home():
    remaining_count = get_remaining_collection_count()
    week_counts = get_last7_job_counts()
    return render_template('home/app.html', remaining_count=remaining_count, week_counts=week_counts)


@main_bp.route('/test')
def test():
    remaining_count = get_remaining_collection_count()
    week_counts = get_last7_job_counts()
    return render_template('home/app.html', remaining_count=remaining_count, week_counts=week_counts)