from flask import Blueprint, jsonify, request

from database import get_cursor
from scheduler.scheduler import generate_schedule, reschedule_after_disruption

schedule_bp = Blueprint('schedule', __name__)


def _serialize(row):
    for field in ('start_time', 'end_time'):
        row[field] = row[field].isoformat()
    return row


@schedule_bp.get('')
def list_schedule():
    with get_cursor() as (_, cursor):
        cursor.execute('''SELECT s.id, s.order_id, s.machine_id, o.order_number, o.product_name,
                  s.start_time, s.end_time,
                  TIMESTAMPDIFF(MINUTE, s.start_time, s.end_time) AS duration,
                  GREATEST(0, TIMESTAMPDIFF(MINUTE, o.deadline, s.end_time)) AS delay_minutes,
                  s.status
                  FROM schedule s
                  JOIN orders o ON o.id = s.order_id
                  ORDER BY s.start_time''')
        return jsonify({'status': 'success', 'data': [_serialize(row) for row in cursor.fetchall()]})


@schedule_bp.post('/generate')
def generate():
    return jsonify({'status': 'success', 'message': 'Schedule generated', 'data': generate_schedule()})


@schedule_bp.post('/reschedule')
def reschedule():
    return jsonify({'status': 'success', 'message': 'Schedule recalculated', 'data': reschedule_after_disruption()})
