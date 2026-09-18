import re

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from database import DatabaseError, get_cursor


auth_bp = Blueprint('auth', __name__)
EMAIL_PATTERN = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
USERNAME_PATTERN = re.compile(r'^[A-Za-z0-9_]+$')


def _error(message, status=400):
    return jsonify({'success': False, 'message': message}), status


def _validate_signup(data):
    if not isinstance(data, dict):
        return 'Request body must be a JSON object'
    full_name = str(data.get('full_name', '')).strip()
    username = str(data.get('username', '')).strip()
    email = str(data.get('email', '')).strip().lower()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')
    if not full_name:
        return 'Full name is required'
    if not username:
        return 'Username is required'
    if not email:
        return 'Email is required'
    if not password:
        return 'Password is required'
    if not confirm_password:
        return 'Confirm password is required'
    if len(full_name) < 2:
        return 'Full name must be at least 2 characters long'
    if len(username) < 3 or not USERNAME_PATTERN.fullmatch(username):
        return 'Username must be at least 3 characters and use only letters, numbers, or underscores'
    if not EMAIL_PATTERN.fullmatch(email):
        return 'Please enter a valid email address'
    if not isinstance(password, str) or len(password) < 6:
        return 'Password must be at least 6 characters long'
    if password != confirm_password:
        return 'Passwords do not match'
    return None


@auth_bp.post('/signup')
def signup():
    data = request.get_json(silent=True) or {}
    validation_error = _validate_signup(data)
    if validation_error:
        return _error(validation_error)
    full_name = str(data['full_name']).strip()
    username = str(data['username']).strip()
    email = str(data['email']).strip().lower()
    try:
        with get_cursor() as (connection, cursor):
            cursor.execute('SELECT username, email FROM users WHERE username = %s OR email = %s', (username, email))
            existing = cursor.fetchone()
            if existing:
                return _error('Username or email already exists', 409)
            cursor.execute(
                'INSERT INTO users (full_name, username, email, password_hash, status) VALUES (%s, %s, %s, %s, %s)',
                (full_name, username, email, generate_password_hash(data['password']), 'active'),
            )
            connection.commit()
    except DatabaseError:
        return _error('Unable to create account right now', 503)
    return jsonify({'success': True, 'message': 'Account created successfully'}), 201


@auth_bp.post('/login')
def login():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return _error('Request body must be a JSON object')
    identifier = str(data.get('username', '')).strip()
    password = data.get('password', '')
    if not identifier or not isinstance(password, str) or not password:
        return _error('Username and password are required')
    try:
        with get_cursor() as (_, cursor):
            cursor.execute(
                'SELECT id, full_name, username, email, password_hash FROM users WHERE username = %s OR email = %s',
                (identifier, identifier.lower()),
            )
            user = cursor.fetchone()
    except DatabaseError:
        return _error('Unable to sign in right now', 503)
    try:
        password_matches = bool(user and check_password_hash(user['password_hash'], password))
    except (TypeError, ValueError):
        password_matches = False
    if not password_matches:
        return _error('Invalid username/email or password', 401)
    session.clear()
    session.permanent = bool(data.get('remember_me'))
    session['user_id'] = user['id']
    return jsonify({'success': True, 'message': 'Login successful', 'user': {
        'id': user['id'], 'full_name': user['full_name'], 'username': user['username'], 'email': user['email'],
    }})


@auth_bp.post('/logout')
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})


@auth_bp.get('/me')
def current_user():
    user_id = session.get('user_id')
    if not user_id:
        return _error('Authentication required', 401)
    try:
        with get_cursor() as (_, cursor):
            cursor.execute('SELECT id, full_name, username, email FROM users WHERE id = %s', (user_id,))
            user = cursor.fetchone()
    except DatabaseError:
        return _error('Unable to verify authentication', 503)
    if not user:
        session.clear()
        return _error('Authentication required', 401)
    return jsonify({'success': True, 'user': user})