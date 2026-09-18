from datetime import datetime

from flask import Blueprint, jsonify, request

from database import get_cursor

machines_bp = Blueprint('machines', __name__)


def _serialize(row):
    row['machineId'] = row.pop('machine_id')
    row['machineName'] = row.pop('machine_name')
    row['machineType'] = row.pop('machine_type')
    row['availableFrom'] = row.pop('available_from').isoformat() if row.get('available_from') else None
    row['maintenanceDate'] = row.pop('maintenance_date').isoformat() if row.get('maintenance_date') else None
    row['createdAt'] = row.pop('created_at').isoformat() if row.get('created_at') else None
    return row


@machines_bp.get('')
def list_machines():
    with get_cursor() as (_, cursor):
        cursor.execute('SELECT id, machine_id, machine_name, machine_type, available_from, status, utilization, maintenance_date, created_at FROM machines ORDER BY id')
        return jsonify({'status': 'success', 'data': [_serialize(row) for row in cursor.fetchall()]})


@machines_bp.post('')
def create_machine():
    data = request.get_json(silent=True) or {}
    required = {'id', 'name', 'type'}
    missing = required - data.keys()
    if missing:
        return jsonify({'status': 'error', 'message': f'Missing fields: {", ".join(sorted(missing))}'}), 400
    if not all(str(data[field]).strip() for field in required):
        return jsonify({'status': 'error', 'message': 'id, name, and type cannot be empty'}), 400
    available_from = data.get('availableFrom')
    if available_from:
        try:
            available_from = datetime.fromisoformat(available_from.replace('Z', '+00:00')).replace(tzinfo=None)
        except ValueError:
            return jsonify({'status': 'error', 'message': 'availableFrom must be a valid ISO datetime'}), 400
    else:
        available_from = datetime.now().replace(second=0, microsecond=0)
    query = """INSERT INTO machines (machine_id, machine_name, machine_type, available_from, status, maintenance_date)
               VALUES (%s, %s, %s, %s, %s, %s)"""
    values = (str(data['id']).strip(), str(data['name']).strip(), str(data['type']).strip(), available_from, data.get('status', 'Available'), data.get('maintenanceDate'))
    with get_cursor() as (connection, cursor):
        cursor.execute(query, values)
        connection.commit()
    return jsonify({'status': 'success', 'message': 'Machine created', 'data': {'id': data['id']}}), 201


@machines_bp.put('/<machine_id>')
def update_machine(machine_id):
    data = request.get_json(silent=True) or {}
    allowed = {'name': 'machine_name', 'type': 'machine_type', 'availableFrom': 'available_from', 'status': 'status', 'maintenanceDate': 'maintenance_date', 'utilization': 'utilization'}
    fields, values = [], []
    for key, column in allowed.items():
        if key in data:
            value = data[key]
            if key == 'availableFrom' and value:
                try:
                    value = datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=None)
                except (AttributeError, TypeError, ValueError):
                    return jsonify({'status': 'error', 'message': 'availableFrom must be a valid ISO datetime'}), 400
            fields.append(f'{column} = %s')
            values.append(value)
    if not fields:
        return jsonify({'status': 'error', 'message': 'No valid fields supplied'}), 400
    values.append(machine_id)
    with get_cursor() as (connection, cursor):
        cursor.execute(f"UPDATE machines SET {', '.join(fields)} WHERE id = %s", values)
        if cursor.rowcount == 0:
            return jsonify({'status': 'error', 'message': 'Machine not found'}), 404
        connection.commit()
    return jsonify({'status': 'success', 'message': 'Machine updated'})


@machines_bp.delete('/<machine_id>')
def delete_machine(machine_id):
    with get_cursor() as (connection, cursor):
        cursor.execute('DELETE FROM machines WHERE id = %s', (machine_id,))
        if cursor.rowcount == 0:
            return jsonify({'status': 'error', 'message': 'Machine not found'}), 404
        connection.commit()
    return jsonify({'status': 'success', 'message': 'Machine deleted'})
