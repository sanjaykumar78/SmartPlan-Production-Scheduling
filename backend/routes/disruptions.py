from datetime import datetime

from flask import Blueprint, jsonify, request

from database import get_cursor

_disruptions_bp = Blueprint('disruptions', __name__)
disruptions_bp = _disruptions_bp


def _serialize(row):
    for key in ('start_time', 'end_time', 'created_at'):
        if row.get(key):
            row[key.replace('_time', 'Time').replace('created_at', 'createdAt')] = row.pop(key).isoformat()
    row['machineId'] = row.pop('machine_id')
    row['eventType'] = row.pop('event_type')
    return row


@disruptions_bp.get('')
def list_disruptions():
    with get_cursor() as (_, cursor):
        cursor.execute('SELECT id, event_type, machine_id, start_time, end_time, description, severity, status, created_at FROM disruptions ORDER BY created_at DESC')
        return jsonify({'status': 'success', 'data': [_serialize(row) for row in cursor.fetchall()]})


@disruptions_bp.post('')
def create_disruption():
    data = request.get_json(silent=True) or {}
    required = {'eventType', 'startTime'}
    missing = required - data.keys()
    if missing:
        return jsonify({'status': 'error', 'message': f'Missing fields: {", ".join(sorted(missing))}'}), 400
    try:
        start_time = datetime.fromisoformat(data['startTime'].replace('Z', '+00:00')).replace(tzinfo=None)
        end_time = datetime.fromisoformat(data['endTime'].replace('Z', '+00:00')).replace(tzinfo=None) if data.get('endTime') else None
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'startTime and endTime must be valid ISO timestamps'}), 400
    query = """INSERT INTO disruptions (event_type, machine_id, start_time, end_time, description, severity, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s)"""
    values = (data['eventType'], data.get('machineId'), start_time, end_time, data.get('description', ''), data.get('severity', 'Medium'), data.get('status', 'Active'))
    with get_cursor() as (connection, cursor):
        cursor.execute(query, values)
        connection.commit()
        event_id = cursor.lastrowid
    return jsonify({'status': 'success', 'message': 'Disruption reported', 'data': {'id': event_id}}), 201
