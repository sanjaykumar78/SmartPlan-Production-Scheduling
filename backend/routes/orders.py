from datetime import datetime

from flask import Blueprint, jsonify, request

from database import get_cursor

orders_bp = Blueprint('orders', __name__)
REQUIRED_FIELDS = {'id', 'product', 'quantity', 'processingTime', 'priority', 'deadline'}
VALID_PRIORITIES = {'High', 'Medium', 'Low'}


def _parse_datetime(value, field_name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{field_name} must be an ISO datetime string')
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=None)
    except ValueError as error:
        raise ValueError(f'{field_name} must be a valid ISO datetime') from error


def _order_payload(data):
    missing = REQUIRED_FIELDS - data.keys()
    if missing:
        raise ValueError(f'Missing fields: {", ".join(sorted(missing))}')
    if not str(data['id']).strip() or not str(data.get('productName', data['product'])).strip():
        raise ValueError('id and product are required')
    if data['priority'] not in VALID_PRIORITIES:
        raise ValueError('priority must be High, Medium, or Low')
    quantity = int(data['quantity'])
    processing_time = int(data['processingTime'])
    if quantity <= 0 or processing_time <= 0:
        raise ValueError('quantity and processingTime must be greater than zero')
    return (
        str(data['id']).strip(), data.get('productName', data['product']).strip(), quantity, processing_time,
        data['priority'], _parse_datetime(data['deadline'], 'deadline'),
        str(data.get('requiredMachineType', data.get('machineType', 'CNC'))).strip(), data.get('status', 'Pending'), data.get('notes'),
    )


def _serialize(row):
    row['orderNumber'] = row.pop('order_number')
    row['productName'] = row.pop('product_name')
    row['processingTime'] = row.pop('processing_time')
    row['requiredMachineType'] = row.pop('required_machine_type')
    row['deadline'] = row['deadline'].isoformat() if row.get('deadline') else None
    row['createdAt'] = row.pop('created_at').isoformat() if row.get('created_at') else None
    return row


@orders_bp.get('')
def list_orders():
    with get_cursor() as (_, cursor):
        cursor.execute('SELECT id, order_number, product_name, quantity, processing_time, priority, deadline, required_machine_type, status, notes, created_at FROM orders ORDER BY deadline ASC')
        return jsonify({'status': 'success', 'data': [_serialize(row) for row in cursor.fetchall()]})


@orders_bp.post('')
def create_order():
    try:
        values = _order_payload(request.get_json(silent=True) or {})
    except (TypeError, ValueError, KeyError) as error:
        return jsonify({'status': 'error', 'message': str(error)}), 400
    query = """INSERT INTO orders (order_number, product_name, quantity, processing_time, priority, deadline, required_machine_type, status, notes)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
    with get_cursor() as (connection, cursor):
        cursor.execute(query, values)
        connection.commit()
    return jsonify({'status': 'success', 'message': 'Production order created', 'data': {'orderNumber': values[0]}}), 201


@orders_bp.put('/<order_id>')
def update_order(order_id):
    data = request.get_json(silent=True) or {}
    allowed = {'orderNumber': 'order_number', 'productName': 'product_name', 'quantity': 'quantity', 'processingTime': 'processing_time', 'priority': 'priority', 'deadline': 'deadline', 'requiredMachineType': 'required_machine_type', 'status': 'status', 'notes': 'notes'}
    fields = []
    values = []
    for key, column in allowed.items():
        if key in data:
            value = data[key]
            if key == 'deadline':
                try:
                    value = _parse_datetime(value, 'deadline')
                except ValueError as error:
                    return jsonify({'status': 'error', 'message': str(error)}), 400
            if key in {'quantity', 'processingTime'}:
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    return jsonify({'status': 'error', 'message': f'{key} must be an integer'}), 400
                if value <= 0:
                    return jsonify({'status': 'error', 'message': f'{key} must be greater than zero'}), 400
            if key == 'priority' and value not in VALID_PRIORITIES:
                return jsonify({'status': 'error', 'message': 'priority must be High, Medium, or Low'}), 400
            fields.append(f'{column} = %s')
            values.append(value)
    if not fields:
        return jsonify({'status': 'error', 'message': 'No valid fields supplied'}), 400
    values.append(order_id)
    with get_cursor() as (connection, cursor):
        cursor.execute(f"UPDATE orders SET {', '.join(fields)} WHERE id = %s", values)
        if cursor.rowcount == 0:
            return jsonify({'status': 'error', 'message': 'Order not found'}), 404
        connection.commit()
    return jsonify({'status': 'success', 'message': 'Production order updated'})


@orders_bp.delete('/<order_id>')
def delete_order(order_id):
    with get_cursor() as (connection, cursor):
        cursor.execute('DELETE FROM orders WHERE id = %s', (order_id,))
        if cursor.rowcount == 0:
            return jsonify({'status': 'error', 'message': 'Order not found'}), 404
        connection.commit()
    return jsonify({'status': 'success', 'message': 'Production order deleted'})
