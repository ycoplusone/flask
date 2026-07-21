from flask import Blueprint, render_template, request

from app.logics.survey_join import get_survey_chart_data, get_survey_table_rows

survey_join = Blueprint('survey_join', __name__)


@survey_join.route('/survey_join', methods=['GET', 'POST'])
def survey_join1():
    base_mm = request.values.get('base_mm', '')
    url = request.values.get('url', '%')

    sales_data, expense_data, months_data = get_survey_chart_data(base_mm)
    table_rows = get_survey_table_rows(base_mm, url)

    return render_template(
        'survey/survey_join.html',
        base_mm=base_mm,
        url=url,
        sales_data=sales_data,
        expense_data=expense_data,
        months_data=months_data,
        table_rows=table_rows,
    )


