# project/server/config.py

import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    DEBUG = False
    TESTING = False
    SECRET_KEY = 'base'
    REDIS_URL = "redis://redis:6379/0"
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
  
 
   
from redis import Redis
redis = Redis(host='redis', port=6379)

def getRedis():
    return redis
 
        
        
def getConfig():
    if not redis.get('value'):
        redis.set('value', 0.5)

    if not redis.get('do_pass'):
        redis.set('do_pass', 0)
        
    if not redis.get('do_geo'):
        redis.set('do_geo', 0)        

    if not redis.get('do_save'):
        redis.set('do_save', 0)

    if not redis.get('do_analyze'):
        redis.set('do_analyze', 0)
        
    cfg = {
            "value": float(redis.get('value')), 
            "do_pass": float(redis.get('do_pass')),
            "do_geo": float(redis.get('do_geo')),
            "do_save": float(redis.get('do_save')),
            "do_analyze": float(redis.get('do_analyze'))
          }
    
    return cfg    
