from flask import Blueprint, jsonify

from database import get_cursor

reports_bp = Blueprint('reports', __name__)


@reports_bp.get('')
def reports():
    with get_cursor() as (_, cursor):
        cursor.execute("SELECT COUNT(*) AS totalOrders, COALESCE(SUM(quantity), 0) AS totalProduction, COALESCE(AVG(processing_time), 0) AS averageProcessingTime FROM orders")
        overview = cursor.fetchone()
        cursor.execute("SELECT status, COUNT(*) AS count FROM orders GROUP BY status")
        order_status = cursor.fetchall()
        cursor.execute("SELECT id, utilization, status FROM machines ORDER BY utilization DESC")
        machine_utilization = cursor.fetchall()
        cursor.execute("SELECT DATE(start_time) AS day, COUNT(*) AS entries FROM schedule GROUP BY DATE(start_time) ORDER BY day")
        daily_schedule = cursor.fetchall()
    return jsonify({'status': 'success', 'data': {'overview': overview, 'orderStatus': order_status, 'machineUtilization': machine_utilization, 'dailySchedule': daily_schedule}})
