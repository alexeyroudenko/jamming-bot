from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS, cross_origin

from config import getConfig, getRedis
cfg = getConfig()
redis = getRedis()
app = Flask(__name__, 
    static_url_path='/static', 
    static_folder='../static', 
    template_folder='../templates'
)
cors = CORS(app)    
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
    
    
    
    
def get_socketio():
    return socketio

def create_app():
    from werkzeug.middleware.proxy_fix import ProxyFix
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
    
    return app
