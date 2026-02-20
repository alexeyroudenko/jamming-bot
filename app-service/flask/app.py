import os
import sys
import time
import json
import logging
import requests

from flask import Flask, Response, Blueprint, jsonify, request, redirect, render_template
from flask_cors import CORS, cross_origin
from flask_socketio import SocketIO, emit
from werkzeug.middleware.proxy_fix import ProxyFix
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

from rq_helpers import queue, get_all_jobs
from config import Config, getConfig, getRedis
import jobs

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
SVC_NAME = "app-service"
SENTRY_DSN = os.getenv('SENTRY_DSN', '')
TAGS_SERVICE_URL = os.getenv('TAGS_SERVICE_URL', 'http://tags_service:8000')

cfg = getConfig()
redis = getRedis()

# ---------------------------------------------------------------------------
# Sentry
# ---------------------------------------------------------------------------

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            LoggingIntegration(level=logging.DEBUG, event_level=logging.INFO),
        ],
        enable_logs=True,
        environment=ENVIRONMENT,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        send_default_pii=False,
    )

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.DEBUG,
    format=f'[{SVC_NAME}] %(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)
logger.info(f"Sentry initialized for environment: {ENVIRONMENT}" if SENTRY_DSN else "Sentry not configured")

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

base_dir = os.path.dirname(os.path.abspath(__file__))
static_folder = os.path.join(base_dir, 'static')
template_folder = os.path.join(base_dir, 'templates')

app = Flask(
    __name__,
    static_url_path='/flask_static',
    static_folder=static_folder,
    template_folder=template_folder,
)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config.from_object('config.Config')

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------

metrics = PrometheusMetrics(app)
step_number = Gauge('step_number', 'Current step number')
steps_forwards = Gauge('steps_forwards', 'Steps remaining')

# ---------------------------------------------------------------------------
# CORS & SocketIO
# ---------------------------------------------------------------------------

cors = CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://jamming-bot.arthew0.online:3000",
            "http://localhost:3000",
            "https://jamming-bot.arthew0.online",
            "http://jamming-bot.arthew0.online",
        ]
    }
})

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading", manage_session=False)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DO_RED = False

def send_node_red_event(event):
    if DO_RED:
        try:
            requests.post("http://node_red:1880/events/debug/", {"event": event})
        except Exception as e:
            print("error ", e)


def _ensure_redis_defaults():
    defaults = {'value': 0.5, 'do_pass': 0.5, 'do_geo': 0.5,
                'do_save': 0.5, 'do_analyze': 0.5, 'do_screenshot': 0.5}
    for key, default in defaults.items():
        if not redis.get(key):
            redis.set(key, default)
    return {k: float(redis.get(k)) for k in defaults}


def _tags_response_json(r):
    """Safely get JSON from a tags_service response."""
    if not r.text or not r.text.strip():
        return None
    ct = r.headers.get("Content-Type", "")
    if "application/json" not in ct:
        return None
    try:
        return r.json()
    except (ValueError, requests.exceptions.JSONDecodeError):
        return None


BASE_TEXT = (
    "Jammingbot is a fantasy about a post-apocalyptic future, when the main "
    "functions of the Internet and assistant bots are defeated and only one "
    "self-replicating bot remains, aimlessly plowing the Internet. This is a "
    "bot that has no goal, only a path. Currently, spiders, crawlers and bots "
    "have a service purpose. They act as search engines, collect information, "
    "automate Internet infrastructure. Jammingbot is a fantasy about a "
    "post-apocalyptic future where the core functions of the internet and "
    "assistant bots have been defeated and only one self-replicating bot "
    "remains, aimlessly browsing the internet, perhaps studying the general "
    "mood of humanity in the fragments of meaning on the pages of the "
    "internet. It is a bot that has no goal, only a path."
)


# =========================================================================
#  HTTP Routes (from http_routes.py)
# =========================================================================

@app.route('/')
@cross_origin()
def bot():
    return render_template('bot.html')


@app.route('/status')
def status():
    return jsonify({"status": "ok"})


@app.route('/help/')
def help_page():
    return render_template('help.html')


@app.route('/metrics')
def metrics_endpoint():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.route('/delete_job/<job_id>', methods=["GET"])
def deletejob(job_id):
    job = queue.fetch_job(job_id)
    job.delete()
    return redirect('/queue/')


@app.route("/jobs/<job_id>", methods=["GET"])
def get_job_status(job_id):
    job = queue.fetch_job(job_id)
    if job:
        return jsonify({
            "status": "success",
            "data": {
                "job_id": job.get_id(),
                "job_status": job.get_status(),
                "job_result": job.result,
            },
        }), 200
    return jsonify({"message": "job not found"}), 500


@app.route("/queue/", methods=["GET"])
def queue_page():
    joblist = reversed(get_all_jobs())
    l = []
    for job in list(joblist):
        l.append({
            'id': job.get_id(),
            'state': job.get_status(),
            'type': job.meta.get('type'),
            'progress': job.meta.get('progress'),
            'result': job.result,
        })
    return render_template('queue.html', joblist=l, cfg=_ensure_redis_defaults())


@app.route("/ctrl/", methods=["GET"])
def ctrl():
    return render_template('ctrl.html', cfg=_ensure_redis_defaults())


@app.route("/set/<v>/", methods=["GET"])
def set_value(v):
    redis.set('value', v)
    socketio.emit('set', {"value": v})
    return "set"


@app.route("/set_values/", methods=["POST"])
def set_values():
    if request.method == 'POST':
        data = request.form.to_dict()
        socketio.emit('set_values', data)
    return "set"


@app.route("/ctrl/<action>/", methods=["GET"])
def ctrl_action(action):
    redis.publish('ctrl', json.dumps(action))
    return redirect('/ctrl/')


@app.route("/api/tags/add_tags_from_steps/", methods=["GET"])
def add_tags_from_steps():
    jobs.add_tags_from_steps.delay()
    return "ok"


@app.route("/api/tags/clean/", methods=["GET"])
def clean_tags():
    jobs.clean_tags.delay()
    return "ok"


@app.route("/api/tags/get/", methods=["GET"])
def get_tags():
    url = f"{TAGS_SERVICE_URL}/api/v1/tags/tags/group/"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return jsonify(response.json()), 200
    except requests.exceptions.ConnectionError as e:
        return jsonify({"error": "Tags service unreachable", "detail": str(e)}), 503
    except requests.exceptions.Timeout:
        return jsonify({"error": "Tags service timeout"}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Tags service error", "detail": str(e)}), 502


@app.route('/bot/events/<event_id>/', methods=['POST'])
def bot_event(event_id):
    logger.info(f"bot_event received: {event_id}")
    if request.method == 'POST':
        socketio.emit('event', {"event": event_id, "data": {}})

        if event_id == "steps_forwards":
            form_data = request.form.to_dict()
            value = int(form_data.get('steps_forwards', form_data.get('data', 0)))
            steps_forwards.set(value)
            logger.info(f"steps_forwards set to {value} form_keys={list(form_data.keys())}")
            socketio.emit('steps_forwards', value)
    return "event"


@app.route('/bot/sublink/add/', methods=['POST'])
def sublink_add():
    if request.method == 'POST':
        data = request.form.to_dict()
        socketio.emit('sublink', data)
    return "step"


@app.route('/bot/step/', methods=['GET', 'POST'])
def step():
    logger.info("step start")
    if request.method == 'POST':
        current_cfg = getConfig()
        data = request.form.to_dict()

        step_number.set(int(data['number']))
        data['step'] = data['number']
        data['id'] = data['url']
        data['current_url'] = data['url']
        data['src_url'] = data['src']
        data['status_string'] = "ok" if str(data['status_code']) == "200" else "error"
        data['struct_text'] = data['text']
        data['semantic'] = ""
        data['semantic_words'] = ""

        # PASS — semantic analysis via worker
        if float(current_cfg['do_pass']) == 1.0:
            socketio.emit('step', data)
            if len(data['text']) > 0:
                jobs.dostep.delay(data)
        else:
            socketio.emit('step', data)

        # GEO
        if float(current_cfg['do_geo']) == 1.0:
            send_node_red_event(f"try {data.keys()}")
            if "ip" in data.keys():
                ip = data['ip']
                if ip != "0":
                    job = jobs.do_geo.delay(ip)
                    while True:
                        time.sleep(0.01)
                        job.refresh()
                        if job.is_finished:
                            socketio.emit('location', job.result)
                            break

        # ANALYZE
        if float(current_cfg['do_analyze']) == 1.0:
            html = data.get('html', data.get('text', ''))
            job = jobs.analyze.delay(html)
            while True:
                time.sleep(0.01)
                job.refresh()
                if job.is_finished:
                    data['analyzed'] = job.result
                    socketio.emit('analyzed', job.result)
                    break

        # SCREENSHOT
        if data.get('url'):
            job = jobs.do_screenshot.delay(data)
            while True:
                time.sleep(0.01)
                job.refresh()
                if job.is_finished:
                    socketio.emit('screenshot', job.result)
                    break
                if job.is_failed:
                    break

    return "done"


@app.route("/spacy/", methods=['GET', 'POST'])
def spacy_test():
    message_text = "Jammingbot is a fantasy about a post-apocalyptic future."
    url = "http://spacyapi/ent"
    headers = {'content-type': 'application/json'}
    d = {'text': message_text, 'model': 'en_core_web_md'}
    response = requests.post(url, data=json.dumps(d), headers=headers)
    return jsonify(response.json())


@app.route("/screenshoter/", methods=['GET', 'POST'])
def screenshoter():
    url = "http://screenshoter:8080/take?url=https%3A%2F%2Fhub.docker.com%2Fr%2Fmingalevme%2Fscreenshoter%2F"
    response = requests.get(url)
    with open("response.jpg", "wb") as f:
        f.write(response.content)
    return "hello", 200


@app.route("/test/service/", methods=["GET"])
def test_service():
    r = None
    for idd in range(0, 48):
        url = f"{TAGS_SERVICE_URL}/api/v1/tags/{idd}/"
        headers = {'content-type': 'application/json'}
        response = requests.delete(url, headers=headers)
        r = response.json()
    return jsonify(r)


@app.route("/test/service_words/", methods=["GET"])
def words_service():
    word = "hello"
    url = f"{TAGS_SERVICE_URL}/api/v1/tags/"
    headers = {'content-type': 'application/json'}
    data = {'name': word, "count": 0}
    requests.post(url, data=json.dumps(data), headers=headers)
    return jsonify(["ok"])


@app.route('/set_tick/', methods=['GET', 'POST'])
def set_tick():
    redis.publish('ctrl', json.dumps("restart"))
    return redirect('/ctrl/')


@app.route("/add_analyze_job/", methods=['GET', 'POST'])
def add_analyze_job():
    if request.method == 'POST':
        data = request.form
        text = data['text']
        jobs.analyze.delay(text)
    return jsonify({"message": "hello"}), 200


# =========================================================================
#  JSON API Routes (from json_handlers.py)
# =========================================================================

@app.route('/api/data', methods=['POST'])
def handle_json():
    data = request.get_json()
    return jsonify({"received": data})


@app.route("/api/steps/", methods=["GET"])
def all_steps():
    joblist = get_all_jobs()
    l = []
    for job in list(joblist):
        if job.meta.get('type'):
            job_type = job.meta.get('type')
            if job_type == "step":
                if job.result:
                    l.append({
                        'id': job.get_id(),
                        'type': job_type,
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
                    })
                else:
                    l.append({
                        'id': job.get_id(),
                        'type': job_type,
                    })
    return jsonify(l)


@app.route('/api/graph/')
@cross_origin()
def api_graph():
    return jsonify([{"id": 1}, {"id": 2}, {"id": 3}])


@app.route("/api/tags/add_one/", methods=["POST"])
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


@app.route("/api/tags/add/", methods=["POST", "GET"])
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


@app.route("/api/step/<step_num>", methods=["GET"])
def get_step(step_num):
    joblist = get_all_jobs()
    l = []
    for job in list(joblist):
        if job.meta.get('type'):
            job_type = job.meta.get('type')
            if job_type == "step" and job.result and job.result.get('step'):
                if int(job.result['step']) == int(step_num):
                    l.append({
                        'id': job.get_id(),
                        'type': job_type,
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
                    })
    return jsonify(l)


@app.route("/add_wait_job/<num_iterations>", methods=["GET"])
def run_wait_job_get(num_iterations):
    jobs.wait.delay(int(num_iterations))
    return redirect('/queue/')


@app.route('/analyze/data/', methods=['POST'])
def analyze_data():
    data = request.get_json()
    return jsonify({"analyze": data})


@app.route("/semantic/vars/", methods=['GET', 'POST'])
def semantic_vars():
    text = BASE_TEXT
    if request.method == 'POST':
        data = request.form.to_dict()
        if "text" in data:
            text = data['text']
    headers = {'content-type': 'application/json'}
    d = {'text': text, 'model': 'en_core_web_md'}
    return jsonify(d)


@app.route("/semantic/ent/", methods=['GET', 'POST'])
def semantic_ent():
    url = "http://spacyapi/ent"
    headers = {'content-type': 'application/json'}
    d = {'text': BASE_TEXT, 'model': 'en_core_web_md'}
    response = requests.post(url, data=json.dumps(d), headers=headers)
    return jsonify(response.json())


# =========================================================================
#  SocketIO event handlers (from socketio_routes.py)
# =========================================================================

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('message')
def handle_message(data):
    print(f"Message received: {data}")
    socketio.emit('response', {'message': 'Message received!'})

@socketio.on('reset')
def handle_reset():
    print('received reset')

@socketio.on('update')
def handle_update(message):
    data = message['data']
    print('update message: ' + str(data))

@socketio.on('start')
def handle_start():
    print("handle start")
    redis.publish('ctrl', json.dumps("start"))

@socketio.on('stop')
def handle_stop():
    print("handle stop")
    redis.publish('ctrl', json.dumps("stop"))

@socketio.on('restart')
def handle_restart():
    socketio.emit('clear')
    redis.publish('ctrl', json.dumps("restart"))

@socketio.on('step')
def handle_step():
    redis.publish('ctrl', json.dumps("step"))

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

@socketio.on('do_screenshot')
def handle_do_screenshot(value):
    redis.set('do_screenshot', float(value))

@socketio.event
def my_ping():
    socketio.emit('my_pong')


# =========================================================================
#  Entry point
# =========================================================================

if __name__ == '__main__':
    print("start flask 2.1.0")
    socketio.run(app, host='0.0.0.0', allow_unsafe_werkzeug=True, debug=True)
