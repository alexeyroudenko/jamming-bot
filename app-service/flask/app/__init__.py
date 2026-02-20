import os
from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS, cross_origin
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter, Gauge, Histogram, Summary
from config import getConfig, getRedis
cfg = getConfig()
redis = getRedis()

# Get absolute paths for static and template folders
# __file__ is app/app/__init__.py, so we go up one level to app/flask, then to static/templates
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
static_folder = os.path.join(base_dir, 'static')
template_folder = os.path.join(base_dir, 'templates')


import os
import sys
import logging
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
# SVC_NAME = os.getenv("SVC_NAME", "app-service")
SVC_NAME = "app-service"
SENTRY_DSN = "https://74f2e249c0ff771f90f0f69560153ed0@o4508353081573376.ingest.de.sentry.io/4508353103003728"

if SENTRY_DSN:
    logging_integration = LoggingIntegration(
        level=logging.DEBUG,
        event_level=logging.INFO
    )
    
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            logging_integration,
        ],
        enable_logs=True,
        environment=ENVIRONMENT,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        send_default_pii=False,
    )

logging.basicConfig(
    level=logging.DEBUG,
    format=f'[{SVC_NAME}] %(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)
logger.info(f"Sentry initialized for environment: {ENVIRONMENT}" if SENTRY_DSN else "Sentry not configured")  





app = Flask(__name__, 
    static_url_path='/flask_static', 
    static_folder=static_folder, 
    template_folder=template_folder
)

def get_sentry():
    return app


def get_logger():
    return logger

# Log static folder configuration for debugging
import logging
app.logger.info(f'Flask static folder configured: {app.static_folder}')
app.logger.info(f'Flask static URL path: {app.static_url_path}')
if os.path.exists(app.static_folder):
    app.logger.info(f'Static folder exists. Contents: {os.listdir(app.static_folder)}')
else:
    app.logger.warning(f'Static folder does not exist at: {app.static_folder}')

# Initialize Prometheus metrics at module level
# This ensures /metrics endpoint works whether app is imported directly or via create_app()
metrics = PrometheusMetrics(app)
app.logger.info('initializing Prometheus metrics')



# 2. Gauge — текущее значение (может расти и падать)
step_number = Gauge('step_number', 'Текущее количество шагов')
# step_number = 77 

steps_forwards = Gauge('steps_forwards', 'Запас хода')


# Explicitly register /metrics route as fallback to ensure it works
# PrometheusMetrics should auto-register this, but this ensures it's available
@app.route('/metrics')
def metrics_endpoint():
    from flask import Response
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


# Configure CORS to allow development server
cors = CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://jamming-bot.arthew0.online:3000",
            "http://localhost:3000",
            "https://jamming-bot.arthew0.online",
            "http://jamming-bot.arthew0.online"
        ]
    }
})

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading", manage_session=False)
    
def get_metrics():
    return metrics

def get_steps_forwards():
    return steps_forwards

def get_step_number():
    return step_number

def get_socketio():
    return socketio

def get_app():
    return app

def create_app():
    from werkzeug.middleware.proxy_fix import ProxyFix
    
    # PrometheusMetrics is already initialized at module level
    # Apply ProxyFix middleware
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
    )

    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    app.config.from_object('config.Config')

    # Регистрируем модули
    from .http_routes import http_bp
    from .socketio_routes import socketio_handlers
    from .json_handlers import json_bp
    
    app.register_blueprint(http_bp)
    app.register_blueprint(json_bp)

    # Инициализируем SocketIO
    socketio.init_app(app)
    socketio_handlers(socketio)
    
    # Verify the route was registered AFTER all blueprints are registered
    with app.app_context():
        routes = [str(rule) for rule in app.url_map.iter_rules()]
        app.logger.info(f'Registered routes: {routes}')
        metrics_routes = [str(rule) for rule in app.url_map.iter_rules() if 'metrics' in str(rule).lower()]
        if metrics_routes:
            app.logger.info(f'✓ Metrics routes found: {metrics_routes}')
        else:
            app.logger.warning('✗ /metrics endpoint NOT found in registered routes')
    
    return app
