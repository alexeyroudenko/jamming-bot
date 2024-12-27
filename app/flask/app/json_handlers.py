import os
import time
import json

from flask import jsonify
from flask import request
from flask import redirect
from flask import Flask, render_template
from flask_cors import CORS, cross_origin
from flask_socketio import SocketIO, emit

import jobs
from rq_helpers import queue, get_all_jobs

from flask import Blueprint, request, jsonify



from config import getConfig, getRedis
cfg = getConfig()
redis = getRedis()
    


json_bp = Blueprint('json', __name__)

@json_bp.route('/api/data', methods=['POST'])
def handle_json():
    data = request.get_json()
    return jsonify({"received": data})


@json_bp.route("/queue/", methods=["GET"])
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


@json_bp.route("/ctrl/", methods=["GET"])
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



# endpoint for getting a job
@json_bp.route("/api/steps/", methods=["GET"])
def all_jobs():
    joblist = get_all_jobs()    
    l = []
    for job in list(joblist):
        if job.meta.get('type'):            
            # app.logger.info(f"job.result {job.result}") 
            job_type = job.meta.get('type')
            if job_type == "step" and job.result:
                l.append({
                    'id': job.get_id(),
                    'type': job.meta.get('type'), 
                    'step': int(job.result['step']),
                    'status_code': int(job.result['code']),
                    'status_string': "ok" if str(job.result['code']) == "200" else "error",
                    'url': job.result['url'],
                    'src_url': job.result['src_url'],
                    'semantic': job.result['semantic'],
                        # 'state': job.get_status(),
                        # 'progress': job.meta.get('progress'),
                        # 'step': job.meta.get('step'),
                        # 'username': job.meta.get('step')['current_url'],
                        # 'r': job.result['words_count'],
                        # 'step': job.result
                    })
    return jsonify(l)


@json_bp.route('/api/graph/')
@cross_origin()
def api_graph():
    response = jsonify([{"id":1},{"id":2},{"id":3}])
    return response


@json_bp.route("/api/step/<step_num>", methods=["GET"])
def get_step(step_num):
    joblist = get_all_jobs()    
    l = []
    for job in list(joblist):
        if job.meta.get('type'):            
            app.logger.info(f"job.result {job.result}") 
            job_type = job.meta.get('type')
            if job_type == "step":
                if int(job.result['step']) == int(step_num):
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
                        'result': job.result
                        })
    return jsonify(l)

# endpoint for adding job
@json_bp.route("/add_wait_job/<num_iterations>", methods=["GET"])
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
@json_bp.route('/delete_job/<job_id>', methods=["GET"])
def deletejob(job_id):
    job = queue.fetch_job(job_id)
    job.delete()
    return redirect('/queue/')


# endpoint for getting a job
@json_bp.route("/jobs/<job_id>", methods=["GET"])
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