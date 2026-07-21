from flask import Blueprint, jsonify

from app.logics.nicon import get_nicon_sales_rows

nicon_api_bp = Blueprint('nicon_api', __name__)


@nicon_api_bp.route('/sales' , methods=['GET'])
def get_nicon_sales_data():
    try:
        rows = get_nicon_sales_rows()
        print("|"*100)
        print(rows)
        return jsonify({
            'rows': rows,
            'error_message': None,
        })
    except Exception as exc:
        return jsonify({
            'rows': [],
            'error_message': f"데이터를 불러오지 못했습니다: {exc}",
        }), 500

