import os
import time
import json

from flask import jsonify
from flask import request
from flask import redirect
from flask import Flask, render_template
from flask_cors import CORS, cross_origin
from flask_socketio import SocketIO, emit

from rq_helpers import queue, get_all_jobs
import jobs



# import sentry_sdk
# sentry_sdk.init(
#     dsn=os.getenv('SHHH_SENTRY_URL'),
#     traces_sample_rate=1.0,
# )
# import logging
# log = logging.getLogger('werkzeug')
# log.setLevel(logging.WARNING)
# redis.set('value', 0.5)
# redis.set('do_pass', 0)
# redis.set('do_save', 0)
# redis.set('do_analyze', 0)

from app import create_app, get_socketio

app = create_app()        
socketio = get_socketio()

if __name__ == '__main__':
    print("start flask 2.1.0")         
    socketio.run(app, host='0.0.0.0', allow_unsafe_werkzeug=True, debug=True)