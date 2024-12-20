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


from redis import Redis

import os
# import sentry_sdk
# sentry_sdk.init(
#     dsn=os.getenv('SHHH_SENTRY_URL'),
#     traces_sample_rate=1.0,
# )

redis = Redis(host='redis', port=6379)
# redis.set('value', 0.5)
# redis.set('do_pass', 0)
# redis.set('do_save', 0)
# redis.set('do_analyze', 0)


app = Flask(__name__, 
    static_url_path='/data', 
    static_folder='data', 
    template_folder='templates'
)

# import logging
# log = logging.getLogger('werkzeug')
# log.setLevel(logging.WARNING)

from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)

app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading") 
cors = CORS(app)



def getConfig():
    if not redis.get('value'):
        redis.set('value', 0.5)

    if not redis.get('do_pass'):
        redis.set('do_pass', 1)
        
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


@app.route('/')
@cross_origin()
def bot():
    return render_template('bot.html')

@app.route('/help/')
def help():
    return render_template('help.html')

@app.route('/api/graph/')
@cross_origin()
def api_graph():
    response = jsonify([{"id":1},{"id":2},{"id":3}])
    return response








# endpoint for monitoring all job status
@app.route("/queue/", methods=["GET"])
def index():
    joblist = reversed(get_all_jobs())
    
    l = []
    # work on copy of joblist
    for job in list(joblist):
        #app.logger.info(f"job {job}")
        l.append({
            'id': job.get_id(),
            'state': job.get_status(),
            'type': job.meta.get('type'),
            'progress': job.meta.get('progress'),
            'result': job.result
            })
        #print(job)
    
    if not redis.get('value'):
        redis.set('value', 0.5)

    if not redis.get('do_pass'):
        redis.set('do_pass', 0.5)
        
    if not redis.get('do_geo'):
        redis.set('do_geo', 0.5)        

    if not redis.get('do_save'):
        redis.set('do_save', 0.5)

    if not redis.get('do_analyze'):
        redis.set('do_analyze', 0.5)

    cfg = {
            "value": float(redis.get('value')), 
            "do_pass": float(redis.get('do_pass')),
            "do_geo": float(redis.get('do_geo')),
            "do_save": float(redis.get('do_save')),
            "do_analyze": float(redis.get('do_analyze'))
          }
    return render_template('queue.html', joblist=l, cfg=cfg)



# endpoint for monitoring all job status
@app.route("/ctrl/", methods=["GET"])
def ctrl():
    
    if not redis.get('value'):
        redis.set('value', 0.5)

    if not redis.get('do_pass'):
        redis.set('do_pass', 0.5)
        
    if not redis.get('do_geo'):
        redis.set('do_geo', 0.5)        

    if not redis.get('do_save'):
        redis.set('do_save', 0.5)

    if not redis.get('do_analyze'):
        redis.set('do_analyze', 0.5)

    cfg = {
            "value": float(redis.get('value')), 
            "do_pass": float(redis.get('do_pass')),
            "do_geo": float(redis.get('do_geo')),
            "do_save": float(redis.get('do_save')),
            "do_analyze": float(redis.get('do_analyze'))
          }
    
    return render_template('ctrl.html', cfg=cfg)







# endpoint for monitoring all job status
@app.route("/rq/", methods=["GET"])
def rq():
    joblist = get_all_jobs()
    
    l = []
    # work on copy of joblist
    for job in list(joblist):
        l.append({
            'id': job.get_id(),            
            'state': job.get_status(),
            'type': job.meta.get('type'),
            'progress': job.meta.get('progress'),
            'result': job.result
        })

    return render_template('index.html', joblist=l)

# endpoint for getting a job
@app.route("/api/steps/", methods=["GET"])
def all_jobs():
    joblist = get_all_jobs()    
    l = []
    for job in list(joblist):
        if job.meta.get('type'):
            
            app.logger.info(f"job.result {job.result}") 
            job_type = job.meta.get('type')
            if job_type == "step":
                l.append({
                    'id': job.get_id(),
                    'type': job.meta.get('type'), 
                    'step': int(job.result['step']),
                    'status_code': int(job.result['code']),
                    'status_string': "ok" if str(job.result['code']) == "200" else "error",
                    'url': job.result['url'],
                    'src_url': job.result['src_url'],
                        # 'state': job.get_status(),
                        # 'progress': job.meta.get('progress'),
                        # 'step': job.meta.get('step'),
                        # 'username': job.meta.get('step')['current_url'],
                        # 'r': job.result['words_count'],
                        # 'step': job.result
                    })
    return jsonify(l)


# endpoint for adding job
@app.route("/add_wait_job/<num_iterations>", methods=["GET"])
def run_wait_job_get(num_iterations):
    num_iterations = int(num_iterations)
    job = jobs.wait.delay(num_iterations)
    response_object = {
        "status": "success",
        "data": {
            "job_id": job.get_id()
        }
    }
    status_code = 200
    return redirect('/queue/')


# endpoint for deleting a job
@app.route('/delete_job/<job_id>', methods=["GET"])
def deletejob(job_id):
    job = queue.fetch_job(job_id)
    job.delete()
    return redirect('/queue/')


# endpoint for getting a job
@app.route("/jobs/<job_id>", methods=["GET"])
def get_status(job_id):
    job = queue.fetch_job(job_id)
    if job:
        response_object = {
            "status": "success",
            "data": {
                "job_id": job.get_id(),
                "job_status": job.get_status(),
                "job_result": job.result,
            },
        }
        status_code = 200
    else:
        response_object = {"message": "job not found"}
        status_code = 500
    return jsonify(response_object), status_code



#
# Controlling BOT
#
@app.route("/ctrl/<action>/", methods=["GET"])
def ctrl_action(action):
    redis.publish('ctrl', json.dumps(action))
    return redirect('/ctrl/')

# endpoint for deleting a job
@app.route('/set_tick/', methods=['GET', 'POST'])
def set_tick():
    # app.logger.info(request.args['tick'])    
    # tick = request.args['tick']
    CHANNEL_NAME = 'ctrl'
    redis.publish(CHANNEL_NAME, json.dumps("restart"))
    return redirect('/ctrl/')



#
# endpoint for adding job
#
@app.route("/add_analyze_job/", methods=['GET', 'POST'])
def add_analyze_job():
    if request.method == 'POST':        
        data = request.form        
        text = data['text']        
        job = jobs.analyze.delay(text)
        app.logger.info("added analyze job !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        # return "add_analyze_job"
    
    # job = jobs.analyze(data)
    # response_object = {
    #     "status": "success",
    #     "data": {
    #         "job_id": job.get_id()
    #     }
    # }
    status_code = 200
    return redirect('/queue/')







# '''
#
#   Called from container
#   do_save = float(cfg['do_save'])
#   do_analyze = float(cfg['do_analyze'])
#
@app.route('/bot/step/', methods=['GET', 'POST'])
def step():
    
    if request.method == 'POST':
        data = request.form.to_dict()
        cfg = getConfig()  

        
        #
        # PASS
        # 
        if float(cfg['do_pass']) == 1.0:
            
            # socketData = {}
            # socketData['id'] = data['current_url']
            # socketData['step'] = int(data['step'])
            # socketData['url'] = data['current_url']
            # socketData['src_url'] = data['src_url']
            # socketData['text'] = data['text']            
            # socketData['src_url'] = data['src_url']
            
            data['url'] = data['current_url']
            data['id'] = data['url']
            data['status_string'] = "ok" if str(data['status_code']) == "200" else "error"       
            socketio.emit('step', data)
            
            app.logger.info(f"step {data.keys()}") 
            job = jobs.dostep.delay(data)
            
        
        
        #
        # GEO
        #                   
        if float(cfg['do_geo']) == 1.0: 
            ip = data['ip']
            url = data['current_url']
            app.logger.info(f"dopass retrieve ip {ip}") 
            if ip != "0":
                job = jobs.dopass.delay(ip)
                while True:
                    time.sleep(0.01)
                    job.refresh()  
                    if job.is_finished:                    
                        location = job.result                        
                        location['url'] == url                
                        socketio.emit('location', location)


        #
        # SAVE
        #      
        if float(cfg['do_save']) == 1.0:
            # socketio.emit('step', data)
            job = jobs.save.delay(data)
            while True:
                time.sleep(0.01)
                job.refresh() 
                if job.is_finished:
                    # socketio.emit('step', data)
                    filename = job.meta.get('filename')
                    app.logger.info(f"added save {filename}")
                    break

        #
        # ANALYZE
        #
        if float(cfg['do_analyze']) == 1.0:
            app.logger.info(f"analyze data {data['current_url']}")
            job = jobs.analyze.delay(data['html'])
            while True:
                time.sleep(0.01)
                job.refresh()  
                if job.is_finished:
                    data['analyzed'] = job.result
                    socketio.emit('analyzed', job.result)
                    break

        # job = jobs.screenshot.delay(data)
        # app.logger.info(f"added screenshot {job}")
        # #  Analyze
        # #
        # job = jobs.analyze.delay(text)
        # while True:
        #     time.sleep(1)
        #     job.refresh()  # Обновляем информацию о статусе задачи
        #     if job.is_finished:
        #         print("Задача завершена, результат:", job.result[0:60])
        #         words = data['text'][0:64]
        #         data["job_id"] = job.get_id()
        #         data["job_status"] = job.get_status()
        #         data['job_result'] = job.result
        #         data['words'] = words
        #         socketio.emit('analyzed', data)
        #         break
        #     elif job.is_failed:
        #         print("Задача завершилась с ошибкой.")
        #         break
        #     else:
        #         print("Ждем завершения задачи...")
 
    return "step"


@app.route('/bot/page/add/', methods=['GET', 'POST'])
def page_addd():
    if request.method == 'POST':
        data = request.form.to_dict()
        # id = data['id']
        # url = data['url']
        # src = data['src_url']
        socketio.emit('page', data)
    return "step"


# '''
#
#    EVENTS
#
@app.route('/bot/events/<event_id>/', methods=['POST'])
def bot_event(event_id):
    if request.method == 'POST':
        data = {}
        # app.logger.info(f"sent socket event {event_id} {data}")
        socketio.emit('event', {"event":event_id, "data":data})
    return "event"

# '''
#
#    SUBLINKS
#
@app.route('/bot/sublink/add/', methods=['POST'])
def sublink_add():
    if request.method == 'POST':
        data = request.form.to_dict()
        app.logger.info(data)
        # id = data['id']
        # url = data['url']
        # src = data['src_url']
        # hostname = data['hostname']
        socketio.emit('sublink', data)
    return "step"








# '''
#     msg.channel 
#     msg.data
# '''
@socketio.on('reset')
def handle_reset():
    print('received reset')
    #redis.incr('hits')

@socketio.on('connect')
def handle_connect(message):
    #data = message['data']з
    print('connect message')

@socketio.on('update')
def handle_update(message):
    # print('update message: ' + str(msg))
    data = message['data']
    print('update message: ' + str(data))
    
@socketio.on('message')
def handle_message(message):
    print('received message: ' + message)    
    redis.incr('hits')
 
 
# '''
#     bot controlss
#     
# '''
@socketio.on('start')
def handle_start():
    redis.publish('ctrl', json.dumps("start"))
    
@socketio.on('stop')
def handle_stop():
    redis.publish('ctrl', json.dumps("stop"))

@socketio.on('restart')
def handle_restart():
    redis.publish('ctrl', json.dumps("restart"))

@socketio.on('step')
def handle_step():
    redis.publish('ctrl', json.dumps("step"))

 
# redis.set('do_pass', float(1))

# '''
#     queue sockets
#     
# '''
@socketio.on('value')
def handle_value(value):    
    redis.set('value', float(value))

@socketio.on('do_pass')
def handle_do_pass(value):
    redis.set('do_pass', float(value))

@socketio.on('do_geo')
def handle_do_geo(value):
    redis.set('do_geo', float(value))
        
@socketio.on('do_save')
def handle_do_save(value):
    redis.set('do_save', float(value))

@socketio.on('do_analyze')
def handle_do_analyze(value):
    redis.set('do_analyze', float(value))



# '''
#     other
#     
# '''
@socketio.event
def my_ping():
    emit('my_pong')

def event_trends_handler(msg):
    print(f"flask event_trends_handler {msg} ")
    emit('tags', msg)
    
    
    
    
if __name__ == '__main__':
    print("start flask 1.1.0") 

    socketio.run(app, host='0.0.0.0', allow_unsafe_werkzeug=True, debug=True)