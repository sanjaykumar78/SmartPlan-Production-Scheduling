from datetime import datetime, timedelta
from math import ceil

from database import get_cursor

PRIORITY_RANK = {'High': 1, 'Medium': 2, 'Low': 3}
ACTIVE_DISRUPTIONS = ('Machine Breakdown', 'Maintenance')
BLOCKING_STATUSES = {'Active', 'Pending'}
UNAVAILABLE_MACHINE_STATUSES = {'Breakdown', 'Maintenance', 'Offline'}


def _priority_key(order):
    """High priority and explicitly urgent orders are considered first."""
    text = f"{order.get('product_name', '')} {order.get('notes', '')}".lower()
    urgent_rank = 0 if 'urgent' in text else 1
    return urgent_rank, PRIORITY_RANK.get(order['priority'], PRIORITY_RANK['Low']), order['deadline'], order['id']


def _overlaps(start, end, other_start, other_end):
    return start < other_end and end > other_start


def _next_open_start(candidate, duration, occupied, blocked):
    """Move a candidate start after every interval it overlaps."""
    start = candidate
    while True:
        end = start + duration
        conflict = next((interval for interval in occupied + blocked if _overlaps(start, end, interval[0], interval[1])), None)
        if not conflict:
            return start, end
        if conflict[1] == datetime.max:
            return None, None
        start = conflict[1]


def _delay_minutes(end_time, deadline):
    return max(0, ceil((end_time - deadline).total_seconds() / 60))


def _serialize(entry):
    return {
        'order_id': entry['order_id'],
        'machine_id': entry['machine_id'],
        'start_time': entry['start_time'].isoformat(),
        'end_time': entry['end_time'].isoformat(),
        'duration': entry['duration'],
        'status': entry['status'],
        'delay_minutes': entry['delay_minutes'],
    }


def generate_schedule():
    """Build and persist a deterministic schedule using interval constraints.

    Existing schedule rows are treated as occupied time. Orders that already have
    a schedule are left unchanged, which makes repeated generation idempotent.
    """
    with get_cursor() as (connection, cursor):
        cursor.execute("""SELECT id, product_name, processing_time, priority, deadline,
                          required_machine_type, status, notes
                          FROM orders
                          WHERE status NOT IN ('Completed', 'Cancelled')
                          ORDER BY deadline, id""")
        orders = sorted(cursor.fetchall(), key=_priority_key)

        cursor.execute("""SELECT id, machine_type, available_from, status
                          FROM machines ORDER BY id""")
        machines = cursor.fetchall()
        available_machines = [machine for machine in machines if machine['status'] not in UNAVAILABLE_MACHINE_STATUSES]

        cursor.execute('SELECT order_id, machine_id, start_time, end_time FROM schedule')
        existing_rows = cursor.fetchall()
        scheduled_order_ids = {row['order_id'] for row in existing_rows}
        occupied = {}
        for row in existing_rows:
            occupied.setdefault(row['machine_id'], []).append((row['start_time'], row['end_time']))

        cursor.execute("""SELECT machine_id, start_time, end_time
                          FROM disruptions
                          WHERE event_type IN (%s, %s) AND status IN (%s, %s)
                          AND machine_id IS NOT NULL""", (*ACTIVE_DISRUPTIONS, *BLOCKING_STATUSES))
        blocked = {}
        for row in cursor.fetchall():
            # An open-ended disruption blocks the machine for the rest of the planning horizon.
            end_time = row['end_time'] or datetime.max
            blocked.setdefault(row['machine_id'], []).append((row['start_time'], end_time))

        results = []
        for order in orders:
            if order['id'] in scheduled_order_ids:
                continue
            candidates = []
            duration = timedelta(minutes=int(order['processing_time']))
            for machine in available_machines:
                if machine['machine_type'].lower() != order['required_machine_type'].lower():
                    continue
                start, end = _next_open_start(
                    machine['available_from'],
                    duration,
                    occupied.get(machine['id'], []),
                    blocked.get(machine['id'], []),
                )
                if start is None:
                    continue
                candidates.append((start, end, machine))
            if not candidates:
                continue

            start, end, machine = min(candidates, key=lambda item: (item[0], item[2]['id']))
            delay_minutes = _delay_minutes(end, order['deadline'])
            entry = {
                'order_id': order['id'],
                'machine_id': machine['id'],
                'start_time': start,
                'end_time': end,
                'duration': int(order['processing_time']),
                'status': 'Delayed' if delay_minutes else 'Scheduled',
                'delay_minutes': delay_minutes,
            }
            occupied.setdefault(machine['id'], []).append((start, end))
            results.append(entry)

        if results:
            cursor.executemany(
                """INSERT INTO schedule (order_id, machine_id, start_time, end_time, status)
                   VALUES (%s, %s, %s, %s, %s)""",
                [(item['order_id'], item['machine_id'], item['start_time'], item['end_time'], item['status']) for item in results],
            )
            cursor.executemany(
                'UPDATE orders SET status = %s WHERE id = %s AND status NOT IN (\'Completed\', \'Cancelled\')',
                [(item['status'], item['order_id']) for item in results],
            )
            connection.commit()
        return [_serialize(item) for item in results]


def reschedule_after_disruption():
    """Clear future planned jobs and rebuild them around current disruptions."""
    with get_cursor() as (connection, cursor):
        cursor.execute("DELETE FROM schedule WHERE status IN ('Scheduled', 'Delayed')")
        cursor.execute("UPDATE orders SET status = 'Pending' WHERE status IN ('Scheduled', 'Delayed')")
        connection.commit()
    return generate_schedule()
