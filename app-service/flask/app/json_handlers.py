import os
import time
import json

import requests

TAGS_SERVICE_URL = os.getenv('TAGS_SERVICE_URL', 'http://tags_service:8000')
from flask import jsonify
from flask import request
from flask import redirect
from flask import Flask, render_template
from flask_cors import CORS, cross_origin
from flask_socketio import SocketIO, emit
from collections import Counter

# import spacy
import jobs
from rq_helpers import queue, get_all_jobs
from flask import Blueprint, request, jsonify



from config import getConfig, getRedis
cfg = getConfig()
redis = getRedis()


def _tags_response_json(r):
    """Safely get JSON from a tags_service response; avoid JSONDecodeError on empty/non-JSON body."""
    if not r.text or not r.text.strip():
        return None
    ct = r.headers.get("Content-Type", "")
    if "application/json" not in ct:
        return None
    try:
        return r.json()
    except (ValueError, requests.exceptions.JSONDecodeError):
        return None


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
    if not redis.get('do_screenshot'):
        redis.set('do_screenshot', 0.5)

    cfg = {
            "value": float(redis.get('value')), 
            "do_pass": float(redis.get('do_pass')),
            "do_geo": float(redis.get('do_geo')),
            "do_save": float(redis.get('do_save')),
            "do_analyze": float(redis.get('do_analyze')),
            "do_screenshot": float(redis.get('do_screenshot'))
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
    if not redis.get('do_screenshot'):
        redis.set('do_screenshot', 0.5)
    cfg = {
            "value": float(redis.get('value')), 
            "do_pass": float(redis.get('do_pass')),
            "do_geo": float(redis.get('do_geo')),
            "do_save": float(redis.get('do_save')),
            "do_analyze": float(redis.get('do_analyze')),
            "do_screenshot": float(redis.get('do_screenshot'))
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
            if job_type == "step":
                if job.result:
                    l.append({
                        'id': job.get_id(),
                        'type': job.meta.get('type'), 
                        'step': int(job.result['step']),
                        'status_code': int(job.result['code']),
                        'status_string': "ok" if str(job.result['code']) == "200" else "error",
                        'url': job.result['url'],
                        'src_url': job.result['src_url'],
                        'text': job.meta.get('text'), 
                        'semantic': job.result['semantic'],
                        'words': job.meta.get('semantic_words'), 
                        'hrases': job.meta.get('semantic_hrases'), 
                        'sim': job.meta.get('sim'), 


                            # 'state': job.get_status(),
                            # 'progress': job.meta.get('progress'),
                            # 'step': job.meta.get('step'),
                            # 'username': job.meta.get('step')['current_url'],
                            # 'r': job.result['words_count'],
                            # 'step': job.result
                        })
                else:
                    l.append({
                        'id': job.get_id(),
                        'type': job.meta.get('type'), 
                    })
                    
    return jsonify(l)



@json_bp.route('/api/graph/')
@cross_origin()
def api_graph():
    response = jsonify([{"id":1},{"id":2},{"id":3}])
    return response


# endpoint set values
@json_bp.route("/api/tags/add_one/", methods=["POST"])
@cross_origin()
def add_tag():
    if request.method == 'POST':
        tag = request.get_json()
        url = f"{TAGS_SERVICE_URL}/api/v1/tags/"
        headers = {'content-type': 'application/json'}
        data = {'name': tag, "count": 0}
        try:
            r = requests.post(url, data=json.dumps(data), headers=headers, timeout=15)
            body = _tags_response_json(r)
            if not r.ok:
                return jsonify({"error": "Tags service error", "status": r.status_code, "detail": body or r.text[:200]}), 502
            return jsonify(f"ok from POST {tag}" if body is None else {"ok": True, "tag": tag, "response": body})
        except requests.exceptions.RequestException as e:
            return jsonify({"error": "Tags service unreachable", "detail": str(e)}), 503
                
        
# endpoint set values
@json_bp.route("/api/tags/add/", methods=["POST", "GET"])
@cross_origin()
def add_tags():
    if request.method == 'GET':
        tag = "hello"
        url = f"{TAGS_SERVICE_URL}/api/v1/tags/"
        headers = {'content-type': 'application/json'}
        data = {'name': tag, "count": 0}
        try:
            r = requests.post(url, data=json.dumps(data), headers=headers, timeout=15)
            body = _tags_response_json(r)
            if not r.ok:
                return jsonify({"error": "Tags service error", "status": r.status_code, "detail": body or r.text[:200]}), 502
            return jsonify({"ok": True, "tag": tag, "response": body} if body is not None else f"ok from GET (status {r.status_code})")
        except requests.exceptions.RequestException as e:
            return jsonify({"error": "Tags service unreachable", "detail": str(e)}), 503

    if request.method == 'POST':
        tags = request.get_json()
        if not tags:
            return jsonify({"error": "No tags provided"}), 400
        last_r = None
        try:
            for tag in tags:
                url = f"{TAGS_SERVICE_URL}/api/v1/tags/"
                headers = {'content-type': 'application/json'}
                data = {'name': tag, "count": 0}
                last_r = requests.post(url, data=json.dumps(data), headers=headers, timeout=15)
                if not last_r.ok:
                    body = _tags_response_json(last_r)
                    return jsonify({"error": "Tags service error", "status": last_r.status_code, "tag": tag, "detail": body or last_r.text[:200]}), 502
            return jsonify({"ok": True, "tags": tags})
        except requests.exceptions.RequestException as e:
            return jsonify({"error": "Tags service unreachable", "detail": str(e)}), 503   


@json_bp.route("/api/step/<step_num>", methods=["GET"])
def get_step(step_num):
    joblist = get_all_jobs()    
    l = []
    for job in list(joblist):
        if job.meta.get('type'):            
            # app.logger.info(f"job.result {job.result}") 
            job_type = job.meta.get('type')
            if job_type == "step" and job.result['step']:
                if int(job.result['step']) == int(step_num):
                    l.append({
                        'id': job.get_id(),
                        'type': job.meta.get('type'), 
                        'step': int(job.result['step']),
                        'status_code': int(job.result['code']),
                        'status_string': "ok" if str(job.result['code']) == "200" else "error",
                        'url': job.result['url'],
                        'src_url': job.result['src_url'],
                                                
                        'text': job.meta.get('text'), 
                        'semantic': job.result['semantic'],
                        'words': job.meta.get('semantic_words'), 
                        'hrases': job.meta.get('semantic_hrases'), 
                        'sim': job.meta.get('sim'), 

                        
                            # 'state': job.get_status(),
                            # 'progress': job.meta.get('progress'),
                            # 'step': job.meta.get('step'),
                            # 'username': job.meta.get('step')['current_url'],
                            # 'r': job.result['words_count'],
                        # 'result': job.result
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



@json_bp.route('/analyze/data/', methods=['POST'])
def analyze():
    data = request.get_json()
    return jsonify({"analyze": data})






# json_bp = Blueprint('json_semantic', __name__ + "_semantic")
#
#
#
#
#
def get_base_text():
    return "Jammingbot is a fantasy about a post-apocalyptic future, when the main functions of the Internet and assistant bots are defeated and only one self-replicating bot remains, aimlessly plowing the Internet. This is a bot that has no goal, only a path. Currently, spiders, crawlers and bots have a service purpose. They act as search engines, collect information, automate Internet infrastructure. Jammingbot is a fantasy about a post-apocalyptic future where the core functions of the internet and assistant bots have been defeated and only one self-replicating bot remains, aimlessly browsing the internet, perhaps studying the general mood of humanity in the fragments of meaning on the pages of the internet. It is a bot that has no goal, only a path."

text = get_base_text()

@json_bp.route("/semantic/vars/", methods=['GET', 'POST']) 
def semantic_vars():    
    text = get_base_text()    
    if request.method == 'POST':
        data = request.form.to_dict()
        if "text" in  data.keys():
            text = data['text']

    headers = {'content-type': 'application/json'}
    d = {'text': text, 'model': 'en_core_web_md'}    
    return jsonify(d)
   
@json_bp.route("/semantic/ent/", methods=['GET', 'POST'])
def semantic_ent():    
    url = "http://spacyapi/ent"
    headers = {'content-type': 'application/json'}
    d = {'text': text, 'model': 'en_core_web_md'}
    response = requests.post(url, data=json.dumps(d), headers=headers)
    return jsonify(response.json())


# @json_bp.route("/semantic/keywords/", methods=['GET', 'POST'])
# def semantic_keywords():
#     text = get_base_text()    
#     if request.method == 'POST':
#         data = request.form.to_dict()
#         if "text" in  data.keys():
#             text = data['text']
    
#     nlp = spacy.load("en_core_web_lg")
#     doc = nlp(text)
#     keywords = [token.text.lower() for token in doc if token.pos_ in ["NOUN", "ADJ"] and not token.is_stop]
#     keyword_counts = Counter(keywords)
#     # print("Top-5 Keywords:")
#     return jsonify(keyword_counts.most_common(20))


# @json_bp.route("/semantic/phrases_verbs/", methods=['GET', 'POST'])
# def phrases_verbs():    
#     text = get_base_text()
#     if request.method == 'POST':
#         data = request.form.to_dict()
#         if "text" in  data.keys():
#             text = data['text']
            
#     nlp = spacy.load("en_core_web_lg")                   
#     doc = nlp(text)
#     noun_hrases = [chunk.text for chunk in doc.noun_chunks]
#     noun_hrases_out = []
#     for i in noun_hrases:
#         if len(i) > 5:
#             noun_hrases_out.append(i)
    
#     verbs = [token.lemma_ for token in doc if token.pos_ == "VERB"]
#     # Find named entities, phrases and concepts
#     # Найти именованные сущности, фразы и концепции
#     entity_out = []
#     for entity in doc.ents:
#         entity_out.append([entity.text, entity.label_])
        
#     data = {
#         "noun_hrases":noun_hrases, 
#         "noun_hrases_out":noun_hrases_out, 
#         "verbs":[token.lemma_ for token in doc if token.pos_ == "VERB"],
#         "entity_out":entity_out
#     }          
#     return jsonify(data)


# @json_bp.route("/semantic/similarities/", methods=['GET', 'POST'])
# def similarities_bp():
            
#     text = get_base_text()            
#     if request.method == 'POST':
#         data = request.form.to_dict()        
#         if "text" in  data.keys():
#             text = data['text']    
            
#     nlp = spacy.load("en_core_web_sm")
#     doc = nlp(text)
#     query = nlp("Jammingbot")
#     similarities = {}

#     for token in doc:
#         if token.has_vector and query.has_vector:
#             similarity = query.similarity(token)
#             if similarity > 0:  # Фильтрация значений, близких к нулю
#                 similarities[token.text] = similarity

#     sorted_similarities = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
        
#     data = {
#         "sorted_similarities":sorted_similarities, 
#         # "noun_hrases_out":noun_hrases_out, 
#         # "verbs":[token.lemma_ for token in doc if token.pos_ == "VERB"],
#         # "entity_out":entity_out
#     }        
        
#     return jsonify(data) 






