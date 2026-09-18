from flask import Flask, jsonify
from flask_cors import CORS

from config import Config
from database import DatabaseError, get_cursor, initialize_database
from routes.disruptions import disruptions_bp
from routes.machines import machines_bp
from routes.orders import orders_bp
from routes.reports import reports_bp
from routes.schedule import schedule_bp
from routes.auth import auth_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app, resources={r'/api/*': {'origins': ['http://127.0.0.1:8000', 'http://localhost:8000']}}, supports_credentials=True)

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(orders_bp, url_prefix='/api/orders')
    app.register_blueprint(machines_bp, url_prefix='/api/machines')
    app.register_blueprint(schedule_bp, url_prefix='/api/schedule')
    app.register_blueprint(disruptions_bp, url_prefix='/api/disruptions')
    app.register_blueprint(reports_bp, url_prefix='/api/reports')

    @app.get('/api/health')
    def health():
        try:
            with get_cursor(dictionary=False) as (_, cursor):
                cursor.execute('SELECT 1')
                cursor.fetchone()
        except DatabaseError as error:
            app.logger.error('Health check database failure: %s', error)
            return jsonify({'status': 'error', 'database': 'disconnected'}), 503
        return jsonify({'status': 'success', 'database': 'connected'})

    @app.errorhandler(DatabaseError)
    def handle_database_error(error):
        return jsonify({'status': 'error', 'message': 'Database operation failed'}), 503

    @app.errorhandler(404)
    def handle_not_found(error):
        return jsonify({'status': 'error', 'message': 'Resource not found'}), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        return jsonify({'status': 'error', 'message': 'HTTP method not allowed'}), 405

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        app.logger.exception('Unhandled API error')
        return jsonify({'status': 'error', 'message': 'Unexpected server error'}), 500

    return app


app = create_app()

if __name__ == '__main__':
    try:
        initialize_database()
    except DatabaseError as error:
        app.logger.warning('Database connection check failed: %s', error)
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
