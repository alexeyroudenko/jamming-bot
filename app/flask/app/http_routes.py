import os
import time
import json
from flask import jsonify
from flask import request
from flask import redirect
from flask import Blueprint, jsonify
from flask_cors import CORS, cross_origin
from flask import Flask, render_template
from rq_helpers import queue, get_all_jobs
import jobs


from config import getConfig, getRedis
cfg = getConfig()
redis = getRedis()

from app import get_socketio
socketio = get_socketio()   



http_bp = Blueprint('http', __name__)

@http_bp.route('/')
@cross_origin()
def bot():
    return render_template('bot.html')

@http_bp.route('/status')
def status():
    return jsonify({"status": "ok"})

@http_bp.route('/help/')
def help():
    return render_template('help.html')




# endpoint for deleting a job
@http_bp.route('/delete_job/<job_id>', methods=["GET"])
def deletejob(job_id):
    job = queue.fetch_job(job_id)
    job.delete()
    return redirect('/queue/')



# endpoint for getting a job
@http_bp.route("/jobs/<job_id>", methods=["GET"])
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


# endpoint for monitoring all job status
@http_bp.route("/queue/", methods=["GET"])
def index():
    joblist = reversed(get_all_jobs())
    
    l = []
    # work on copy of joblist
    for job in list(joblist):
        ## http_bp.logger.info(f"job {job}")
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
@http_bp.route("/ctrl/", methods=["GET"])
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






















#
#   Tests
#
@http_bp.route("/test/service/", methods=["GET"])
def test_service():
    for idd in range(0, 48):
        import requests  
        url = f"http://tags_service:8000/api/v1/tags/{idd}/"
        headers = {'content-type': 'application/json'}
        response = requests.delete(url, headers=headers)
        r = response.json()
    return jsonify(r)

@http_bp.route("/test/service_words/", methods=["GET"])
def words_service():
    word = "hello"
    import json
    import requests
    # url = "http://spacyapi/ent"
    url = "http://tags_service:8000/api/v1/tags/"
    headers = {'content-type': 'application/json'}
    data = {'name': word, "count": 0}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    r = response.json()
    return jsonify(["ok"])

@http_bp.route('/set_tick/', methods=['GET', 'POST'])
def set_tick():
    # # http_bp.logger.info(request.args['tick'])    
    # tick = request.args['tick']
    CHANNEL_NAME = 'ctrl'
    redis.publish(CHANNEL_NAME, json.dumps("restart"))
    return redirect('/ctrl/')

@http_bp.route("/add_analyze_job/", methods=['GET', 'POST'])
def add_analyze_job():
    if request.method == 'POST':        
        data = request.form        
        text = data['text']        
        job = jobs.analyze.delay(text)
    status_code = 200
    response_object = {"message": "hello"}        
    return jsonify(response_object), status_code











#
# Controlling BOT
#
@http_bp.route("/ctrl/<action>/", methods=["GET"])
def ctrl_action(action):
    redis.publish('ctrl', json.dumps(action))
    return redirect('/ctrl/')


# STEP_URL = 'http://flask:5000/bot/step/'
# EVENT_URL = 'http://flask:5000/bot/events'
# SUBLINK_URL = 'http://flask:5000/bot/sublink/add/'




EVENTS_URL = 'http://node_red:1880/events/'

import requests
#
#   EVENTS FROM BOT
# '''
#    EVENTS
@http_bp.route('/bot/events/<event_id>/', methods=['POST'])
def bot_event(event_id):
    
    url = "http://node_red:1880/hello"
    r1 = requests.post(url + "/", data = event_id)    
    r2 = requests.post(url + "/" + event_id + "/", data = event_id)
    
    if request.method == 'POST':
        data = {}
        r = requests.post(EVENTS_URL + event_id + "/", data = data)
        socketio.emit('event', {"event":event_id, "data":data})
    return "event"

# '''
#    SUBLINKS
@http_bp.route('/bot/sublink/add/', methods=['POST'])
def sublink_add():
    if request.method == 'POST':
        data = request.form.to_dict()
        # http_bp.logger.info(data)
        # id = data['id']
        # url = data['url']
        # src = data['src_url']
        # hostname = data['hostname']
        socketio.emit('sublink', data)
    return "step"










@http_bp.route("/spacy/", methods=['GET', 'POST'])
def spacy():    
    """ Semantic """    
    # http_bp.logger.info("hello from spacy")        
    message_text = "Jammingbot is a fantasy about a post-apocalyptic future."
    import json
    import requests
    url = "http://spacyapi/ent"
    headers = {'content-type': 'application/json'}
    d = {'text': message_text, 'model': 'en_core_web_md'}
    response = requests.post(url, data=json.dumps(d), headers=headers)
    r = response.json()
        


@http_bp.route("/screenshoter/", methods=['GET', 'POST'])
def screenshoter():    
    """ Semantic """    
    # http_bp.logger.info("hello from spacy")        
    message_text = "Jammingbot is a fantasy about a post-apocalyptic future."
    import json
    import requests
    # url = "http://screenshoter:8080/take"
    url = "http://screenshoter:8080/take?url=https%3A%2F%2Fhub.docker.com%2Fr%2Fmingalevme%2Fscreenshoter%2F"
    response = requests.get(url)
    with open("response.jpg", "wb") as f:
        f.write(response.content)
        
    status_code = 200    
    return "hello", status_code
















# '''
#
#   Called from container
#   do_save = float(cfg['do_save'])
#   do_analyze = float(cfg['do_analyze'])
#
@http_bp.route('/bot/step/', methods=['GET', 'POST'])
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
                        
            # # http_bp.logger.info(f"step {data.keys()}") 
            job = jobs.dostep.delay(data)
            while True:
                time.sleep(0.01)
                job.refresh()  
                if job.is_finished:                    
                    struct_text = job.result['text']                        
                    data['struct_text'] = struct_text
                    data['semantic'] = job.result['semantic']
                    data['semantic_words'] = job.result['semantic_words']                    
                    # semantic_words_array = data['semantic_words']                                        
                    # words_cloud = calc_counts(semantic_words_array)
                    # data['words_cloud'] = words_cloud                                        
                    socketio.emit('step', data)
                    break          
        
        
        #
        # GEO
        #                   
        if float(cfg['do_geo']) == 1.0:
            if "ip" in data.keys():
                ip = data['ip']
                url = data['current_url']
                ## http_bp.logger.info(f"dopass retrieve ip {ip}") 
                if ip != "0":
                    job = jobs.do_geo.delay(ip)
                    while True:
                        time.sleep(0.01)
                        job.refresh()  
                        if job.is_finished:                    
                            location = job.result                        
                            # location['url'] == url                
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
                    # http_bp.logger.info(f"added save {filename}")
                    break



        #
        # ANALYZE
        #
        # if float(cfg['do_analyze']) == 1.0:
        #     # http_bp.logger.info(f"analyze data {data['current_url']}")
        #     job = jobs.analyze.delay(data['html'])
        #     while True:
        #         time.sleep(0.01)
        #         job.refresh()  
        #         if job.is_finished:
        #             data['analyzed'] = job.result
        #             socketio.emit('analyzed', job.result)
        #             break



        # job = jobs.screenshot.delay(data)
        # # http_bp.logger.info(f"added screenshot {job}")
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
        
        
        

        # endpoint for monitoring all job status
        # @http_bp.route("/rq/", methods=["GET"])
        # def rq():
        #     joblist = get_all_jobs()

        #     l = []
        #     # work on copy of joblist
        #     for job in list(joblist):
        #         l.append({
        #             'id': job.get_id(),            
        #             'state': job.get_status(),
        #             'type': job.meta.get('type'),
        #             'progress': job.meta.get('progress'),
        #             'result': job.result
        #         })
        #     return render_template('index.html', joblist=l)
        # endpoint for getting a job
        # endpoint for getting a job
        # @http_bp.route("/api/step/<step_num>", methods=["GET"])
        # def get_step(step_num):
        #     joblist = get_all_jobs()    
        #     l = []
        #     for job in list(joblist):
        #         if job.meta.get('type'):            
        #             # http_bp.logger.info(f"job.result {job.result}") 
        #             job_type = job.meta.get('type')
        #             if job_type == "step":
        #                 if int(job.result['step']) == int(step_num):
        #                     l.append({
        #                         'id': job.get_id(),
        #                         'type': job.meta.get('type'), 
        #                         'step': int(job.result['step']),
        #                         'status_code': int(job.result['code']),
        #                         'status_string': "ok" if str(job.result['code']) == "200" else "error",
        #                         'url': job.result['url'],
        #                         'src_url': job.result['src_url'],
        #                             # 'state': job.get_status(),
        #                             # 'progress': job.meta.get('progress'),
        #                             # 'step': job.meta.get('step'),
        #                             # 'username': job.meta.get('step')['current_url'],
        #                             # 'r': job.result['words_count'],
        #                         'result': job.result
        #                         })
        #     return jsonify(l)

        # endpoint for adding job
        # @http_bp.route("/add_wait_job/<num_iterations>", methods=["GET"])
        # def run_wait_job_get(num_iterations):
        #     num_iterations = int(num_iterations)
        #     job = jobs.wait.delay(num_iterations)
        #     response_object = {
        #         "status": "success",
        #         "data": {
        #             "job_id": job.get_id()
        #         }
        #     }
        #     status_code = 200
        #     return redirect('/queue/')
        # @http_bp.route('/bot/page/add/', methods=['GET', 'POST'])
        # def page_addd():
        #     if request.method == 'POST':
        #         data = request.form.to_dict()
        #         # id = data['id']
        #         # url = data['url']
        #         # src = data['src_url']
        #         socketio.emit('page', data)
        #     return "step"









        
        
 
    return "step"
