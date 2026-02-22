# project/server/config.py

import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'jamming-bot-secret-key-change-me')
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REDIS_URL = os.getenv('REDIS_URL', "redis://redis:6379/0")
    QUEUES = ["default"]


class ProductionConfig(Config):
    SECRET_KEY = 'prod'


class DevelopmentConfig(Config):
    DEBUG = True
    SECRET_KEY = 'dev'


class TestingConfig(Config):
    DEBUG = True
    TESTING = True
    SECRET_KEY = 'test'
  
 
   
import os as _os
from redis import Redis
redis = Redis(host=_os.getenv('REDIS_HOST', 'redis'), port=int(_os.getenv('REDIS_PORT', '6379')))

def getRedis():
    return redis
 
        
        
def getConfig():
    # Default values if Redis keys don't exist or Redis is read-only
    defaults = {
        'value': 0.5,
        'do_pass': 0,
        'do_geo': 0,
        'do_save': 0,
        'do_analyze': 0,
        'do_screenshot': 0
    }
    
    # Try to initialize default values if they don't exist
    # Handle ReadOnlyError gracefully if Redis is a read-only replica
    try:
        if not redis.get('value'):
            redis.set('value', defaults['value'])
        if not redis.get('do_pass'):
            redis.set('do_pass', defaults['do_pass'])
        if not redis.get('do_geo'):
            redis.set('do_geo', defaults['do_geo'])
        if not redis.get('do_save'):
            redis.set('do_save', defaults['do_save'])
        if not redis.get('do_analyze'):
            redis.set('do_analyze', defaults['do_analyze'])
        if not redis.get('do_screenshot'):
            redis.set('do_screenshot', defaults['do_screenshot'])
    except Exception as e:
        # If Redis is read-only or any other error occurs, use defaults
        # This allows the app to start even if Redis is read-only
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Could not write to Redis (may be read-only): {e}. Using default values.")
    
    # Read values from Redis, falling back to defaults if keys don't exist
    cfg = {}
    for key, default_value in defaults.items():
        try:
            value = redis.get(key)
            if value is not None:
                cfg[key] = float(value)
            else:
                cfg[key] = default_value
        except Exception as e:
            # If read fails, use default
            cfg[key] = default_value
    
    return cfg    
