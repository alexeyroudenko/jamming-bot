import os
import sys
import time
import json
import random
import logging
import threading
import tempfile
import requests

import yaml

from functools import wraps
from flask import Flask, Response, Blueprint, jsonify, request, redirect, render_template, session, url_for
from flask_cors import CORS, cross_origin
from flask_socketio import SocketIO, emit
from werkzeug.middleware.proxy_fix import ProxyFix
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.rq import RqIntegration

from rq_helpers import queue, get_all_jobs, redis_connection
from config import Config, getConfig, getRedis
from telemetry import init_telemetry, inject_trace_context_into_job, set_step_span_attributes, step_span, enqueue_with_trace
import jobs
from tag_embeddings import build_embeddings_response

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
SVC_NAME = "app-service"
SENTRY_DSN = os.getenv('SENTRY_DSN', '')
TAGS_SERVICE_URL = os.getenv('TAGS_SERVICE_URL', 'http://tags_service:8000')
SEMANTIC_SERVICE_URL = os.getenv('SEMANTIC_SERVICE_URL', 'http://semantic_service:8005')
STORAGE_SERVICE_URL = os.getenv('STORAGE_SERVICE_URL', 'http://storage_service:7781')

cfg = getConfig()
redis = getRedis()

# ---------------------------------------------------------------------------
# Sentry
# ---------------------------------------------------------------------------

def _traces_sampler(ctx):
    return 1.0


if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            LoggingIntegration(level=logging.INFO, event_level=logging.WARNING),
            RqIntegration(),
        ],
        enable_logs=True,
        environment=ENVIRONMENT,
        traces_sampler=_traces_sampler,
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

DEFAULT_COMBINE_MAX_PHRASES = 512

# Candidates for GET /api/tags/add/ (one random token per request).
RANDOM_TAG_WORDS = (
    "flow", "signal", "noise", "drift", "pulse", "wave", "node", "edge", "mesh", "field",
    "vector", "orbit", "spark", "shard", "glyph", "trace", "echo", "fog", "haze", "glow",
    "static", "stream", "buffer", "frame", "pixel", "shader", "vertex", "cluster", "lattice",
    "cipher", "token", "syntax", "kernel", "thread", "socket", "packet", "route", "bridge",
    "mirror", "prism", "spectrum", "phase", "amplitude", "resonance", "harmonic", "cadence",
    "entropy", "chaos", "attractor", "manifold", "tensor", "matrix", "gradient", "flux",
    "nebula", "comet", "aurora", "tide", "current", "vapor", "crystal", "fossil", "ember",
    "moth", "raven", "heron", "oak", "lichen", "moss", "root", "branch", "seed", "petal",
    "amber", "jade", "cobalt", "vermilion", "umber", "slate", "obsidian", "marble", "sand",
    "rune", "sigil", "mantra", "verse", "stanza", "folio", "archive", "ledger",
)

# ---------------------------------------------------------------------------
# OpenTelemetry / Jaeger
# ---------------------------------------------------------------------------
init_telemetry(service_name=SVC_NAME)
if os.getenv("OTEL_TRACING_ENABLED", "0") == "1":
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    RequestsInstrumentor().instrument()

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
if os.getenv("OTEL_TRACING_ENABLED", "0") == "1":
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    FlaskInstrumentor().instrument_app(app)

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------

metrics = PrometheusMetrics(app)
step_number = Gauge('step_number', 'Current step number')
steps_forwards = Gauge('steps_forwards', 'Steps remaining')

# ---------------------------------------------------------------------------
# CORS & SocketIO
# ---------------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = frozenset({
    "http://jamming-bot.arthew0.online:3000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://jamming-bot.arthew0.online",
    "http://jamming-bot.arthew0.online",
})
_extra_origins = os.getenv("CORS_EXTRA_ORIGINS", "")
if _extra_origins.strip():
    CORS_ALLOWED_ORIGINS = frozenset(
        CORS_ALLOWED_ORIGINS
        | {o.strip() for o in _extra_origins.split(",") if o.strip()}
    )

cors = CORS(
    app,
    # All paths: fetch() following 302 to /login must still see ACAO (not only /api/*).
    resources={r"/*": {"origins": list(CORS_ALLOWED_ORIGINS)}},
    supports_credentials=True,
)


@app.after_request
def _cors_headers_on_all_responses(response):
    """Ensure ACAO on edge responses (e.g. redirects) if not already set."""
    origin = request.headers.get("Origin")
    if origin in CORS_ALLOWED_ORIGINS:
        response.headers.setdefault("Access-Control-Allow-Origin", origin)
        response.headers.setdefault("Access-Control-Allow-Credentials", "true")
    return response

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet", manage_session=False)

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


AUTH_USER = os.getenv("AUTH_USER", "x")
AUTH_PASS = os.getenv("AUTH_PASS", "x")

PUBLIC_PREFIXES = ("/login", "/status", "/metrics", "/bot/", "/flask_static/",
                   "/tags/", "/geo/", "/screenshots/", "/api/tags/get/", "/api/tags/combine/",
                   "/api/tags/sentiment-vortex/", "/api/tags/embeddings/", "/api/tags/add/",
                   "/api/step/", "/api/steps", "/api/storage_step/", "/api/storage_latest/",
                   "/api/storage_ids/",
                   "/api/storage_geo/")


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated


PUBLIC_PATHS = ("/", "/login")


@app.before_request
def _check_auth():
    if request.method == "OPTIONS":
        return
    if request.path in PUBLIC_PATHS or any(request.path.startswith(p) for p in PUBLIC_PREFIXES):
        return
    if not session.get("logged_in"):
        return redirect(url_for("login", next=request.path))


def _ctrl_log(action: str, source: str):
    ip = request.remote_addr if request else "?"
    logger.info(f"ctrl '{action}' from {source} (ip={ip})")
    redis.publish("ctrl", json.dumps(action))


def _ensure_redis_defaults():
    defaults = {'value': 0.5, 'do_pass': 0.5, 'do_geo': 0.5,
                'do_save': 0.5, 'do_analyze': 0.5, 'do_screenshot': 0.5,
                'do_storage': 0.5, 'sleep_time': 2.0}
    for key, default in defaults.items():
        if not redis.get(key):
            redis.set(key, default)
    return {k: float(redis.get(k)) for k in defaults}


BOT_YAML_KEYS = ("send_events", "send_sublinks", "log_events")


def _read_bot_yaml_flags():
    """Current send_events / send_sublinks / log_events from bot.yaml (same file the bot reloads)."""
    path = (os.getenv("BOT_YAML_PATH") or "").strip()
    out = {k: False for k in BOT_YAML_KEYS}
    if not path or not os.path.isfile(path):
        return out
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            return out
        for k in BOT_YAML_KEYS:
            if k in data and data[k] is not None:
                out[k] = bool(data[k])
    except Exception as e:
        logger.warning("bot.yaml read failed: %s", e)
    return out


def _write_bot_yaml_flags(updates: dict):
    """Merge bool updates into bot.yaml, with a fallback for mounted files."""
    path = (os.getenv("BOT_YAML_PATH") or "").strip()
    if not path:
        raise ValueError("BOT_YAML_PATH is not set")
    for k in updates:
        if k not in BOT_YAML_KEYS:
            raise ValueError(f"invalid bot.yaml key: {k}")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        data = {}
    for k, v in updates.items():
        data[k] = bool(v)
    parent = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp_path = tempfile.mkstemp(prefix="bot_", suffix=".yaml.tmp", dir=parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yaml.safe_dump(
                data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
        os.replace(tmp_path, path)
        return
    except OSError as e:
        # k8s subPath/hostPath single-file mounts can reject rename with EBUSY.
        if e.errno != 16:
            raise
        logger.info("bot.yaml rename failed (%s), falling back to in-place write", e)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            data,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
        f.flush()
        os.fsync(f.fileno())


STEP_HASH_TTL = int(os.getenv('STEP_HASH_TTL', '3600'))


def _save_to_step_hash(step_key, data):
    """Merge *data* dict into the Redis hash at *step_key*."""
    if not step_key or not isinstance(data, dict):
        return
    mapping = {}
    for k, v in data.items():
        if isinstance(v, (dict, list, tuple)):
            mapping[k] = json.dumps(v, default=str)
        elif v is None:
            mapping[k] = ""
        else:
            mapping[k] = str(v)
    try:
        redis.hset(step_key, mapping=mapping)
        redis.expire(step_key, STEP_HASH_TTL)
    except Exception as exc:
        logger.warning(f"_save_to_step_hash({step_key}): {exc}")


def _poll_job_and_emit(job, event_name, timeout=60, poll_interval=0.5,
                       step_key=None, silent=False):
    """Poll an RQ job in a background thread and emit result via SocketIO."""
    def _poll():
        elapsed = 0.0
        while elapsed < timeout:
            time.sleep(poll_interval)
            elapsed += poll_interval
            try:
                job.refresh()
            except Exception:
                logger.debug(f"Job {job.id} no longer exists for event {event_name}")
                return
            if job.is_finished:
                if not silent:
                    socketio.emit(event_name, job.result)
                _save_to_step_hash(step_key, job.result)
                _patch_storage(step_key, job.result)
                return
            if job.is_failed:
                logger.warning(f"Job {job.id} failed for event {event_name}")
                _save_to_step_hash(step_key, {"_error_" + event_name: "job failed"})
                return
        logger.warning(f"Job {job.id} timed out after {timeout}s for event {event_name}")
    threading.Thread(target=_poll, daemon=True).start()


def _read_step_hash(step_key):
    """Read the full aggregated step from the Redis hash, deserialising JSON values."""
    raw = redis.hgetall(step_key)
    if not raw:
        return {}
    result = {}
    for k, v in raw.items():
        key = k.decode() if isinstance(k, bytes) else k
        val = v.decode() if isinstance(v, bytes) else v
        try:
            result[key] = json.loads(val)
        except (json.JSONDecodeError, TypeError):
            result[key] = val
    return result


def _patch_storage(step_key, data):
    """Send incremental update to storage-service via PATCH."""
    number = step_key.split(":")[-1] if step_key else None
    if not number or not data:
        return
    try:
        requests.patch(
            f"{STORAGE_SERVICE_URL}/update/step/{number}",
            json={k: v for k, v in data.items() if not k.startswith('_')},
            timeout=5,
        )
    except Exception as e:
        logger.warning(f"_patch_storage({number}): {e}")


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
#  Auth
# =========================================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form["username"] == AUTH_USER and request.form["password"] == AUTH_PASS:
            session["logged_in"] = True
            return redirect(request.args.get("next") or "/")
        error = "Invalid credentials"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect("/login")


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


@app.route('/screenshots/')
@cross_origin()
def screenshots():
    return render_template('screenshots.html')


@app.route('/tags/')
@cross_origin()
def tags_cloud():
    return render_template('tags.html')


@app.route('/tags/3d/')
@cross_origin()
def tags_cloud_3d():
    return render_template('tags_3d.html')


@app.route('/geo/')
@cross_origin()
def geo_globe():
    return render_template('geo_globe.html')


@app.route('/tags/phrases/')
@cross_origin()
def tags_phrases():
    return render_template('phrases.html')


@app.route('/tags/constellation/')
@cross_origin()
def tags_constellation():
    return render_template('tags_constellation.html')


@app.route('/tags/vectorfield/')
@cross_origin()
def tags_vectorfield():
    return render_template('tags_vectorfield.html')


@app.route('/tags/vectorfield-3d/')
@cross_origin()
def tags_vectorfield_3d():
    return render_template('tags_vectorfield_3d.html')


@app.route('/tags/chaos-attractor/')
@cross_origin()
def tags_chaos_attractor():
    return render_template('tags_chaos_attractor.html')


@app.route('/path/map/')
@cross_origin()
def path_map():
    return render_template('path_map.html')


def _empty_sentiment_stats():
    return {
        "mean_polarity": 0.0,
        "pct_positive": 0.0,
        "pct_negative": 0.0,
        "pct_neutral": 0.0,
        "count": 0,
    }


@app.route('/tags/sentiment-vortex/')
@cross_origin()
def tags_sentiment_vortex():
    return render_template('tags_sentiment_vortex.html')


@app.route('/api/tags/sentiment-vortex/', methods=['GET', 'POST'])
@cross_origin()
def sentiment_vortex_api():
    tags_url = f"{TAGS_SERVICE_URL}/api/v1/tags/tags/group/"
    try:
        tr = requests.get(tags_url, timeout=10)
        tr.raise_for_status()
        tags = tr.json()
    except requests.exceptions.RequestException as e:
        logger.warning("Sentiment vortex tags error: %s", e)
        return jsonify({
            "error": "Tags service unavailable",
            "detail": str(e),
            "phrases": [],
            "stats": _empty_sentiment_stats(),
        }), 502

    if not isinstance(tags, list):
        return jsonify({
            "error": "Invalid tags response",
            "phrases": [],
            "stats": _empty_sentiment_stats(),
        }), 502

    tags.sort(key=lambda t: -(int(t.get("count", 0) or 0)))
    words = [t["name"] for t in tags if t.get("name")]
    if not words:
        return jsonify({
            "phrases": [],
            "stats": _empty_sentiment_stats(),
        })

    combine_url = f"{SEMANTIC_SERVICE_URL}/api/v1/semantic/combine/"
    try:
        cr = requests.post(
            combine_url,
            json={"words": words, "limit": 128, "max_phrases": 256},
            timeout=60,
        )
        cr.raise_for_status()
        cdata = cr.json()
    except requests.exceptions.RequestException as e:
        logger.warning("Sentiment vortex combine error: %s", e)
        return jsonify({
            "error": str(e),
            "phrases": [],
            "stats": _empty_sentiment_stats(),
        }), 502

    phrases = cdata.get("phrases") or []
    sent_url = f"{SEMANTIC_SERVICE_URL}/api/v1/semantic/sentiment-phrases/"
    try:
        sr = requests.post(
            sent_url,
            json={"phrases": phrases, "limit": 256},
            timeout=30,
        )
        sr.raise_for_status()
        sdata = sr.json()
    except requests.exceptions.RequestException as e:
        logger.warning("Sentiment vortex sentiment error: %s", e)
        return jsonify({
            "error": str(e),
            "phrases": [],
            "stats": _empty_sentiment_stats(),
        }), 502

    items = sdata.get("items") or []
    stats = sdata.get("stats") or _empty_sentiment_stats()
    return jsonify({"phrases": items, "stats": stats})


@app.route('/api/tags/combine/', methods=['POST'])
@cross_origin()
def combine_tags_proxy():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "invalid request body", "phrases": []}), 400
    payload = dict(data)
    try:
        max_phrases = int(payload.get("max_phrases", DEFAULT_COMBINE_MAX_PHRASES))
    except (TypeError, ValueError):
        max_phrases = DEFAULT_COMBINE_MAX_PHRASES
    payload["max_phrases"] = max(1, min(max_phrases, DEFAULT_COMBINE_MAX_PHRASES))
    url = f"{SEMANTIC_SERVICE_URL}/api/v1/semantic/combine/"
    try:
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        return jsonify(resp.json())
    except Exception as e:
        logger.warning(f"Combine tags error: {e}")
        return jsonify({"error": str(e), "phrases": []}), 502


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
    try:
        joblist = reversed(get_all_jobs())
    except Exception as e:
        logger.exception("Redis/queue error in queue_page")
        return render_template(
            'queue.html',
            joblist=[],
            cfg={},
            queue_error=str(e)
        ), 503
    from datetime import datetime, timezone

    def _ensure_aware(dt):
        """Make datetime timezone-aware (assume UTC if naive)."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    l = []
    now = datetime.now(timezone.utc)
    for job in list(joblist):
        created_at = getattr(job, 'created_at', None)
        started_at = _ensure_aware(getattr(job, 'started_at', None))
        ended_at = _ensure_aware(getattr(job, 'ended_at', None))
        # Calculate duration: ended-start for finished, now-start for running
        duration_sec = None
        if ended_at and started_at:
            duration_sec = (ended_at - started_at).total_seconds()
        elif started_at:
            duration_sec = (now - started_at).total_seconds()
        l.append({
            'id': job.get_id(),
            'state': job.get_status(),
            'type': job.meta.get('type'),
            'progress': job.meta.get('progress'),
            'result': job.result,
            'created_at': created_at,
            'started_at': started_at,
            'ended_at': ended_at,
            'duration_sec': duration_sec,
        })
    try:
        cfg = _ensure_redis_defaults()
    except Exception as e:
        logger.warning("Redis defaults error: %s", e)
        cfg = {}
    return render_template('queue.html', joblist=l, cfg=cfg)


@app.route("/queue/job/<job_id>/", methods=["GET"])
def queue_job_detail(job_id):
    from datetime import datetime, timezone

    def _ensure_aware(dt):
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    job = queue.fetch_job(job_id)
    if not job:
        return render_template("queue_job.html", job=None, not_found=True), 404

    created_at = getattr(job, "created_at", None)
    started_at = _ensure_aware(getattr(job, "started_at", None))
    ended_at = _ensure_aware(getattr(job, "ended_at", None))
    duration_sec = None
    if ended_at and started_at:
        duration_sec = (ended_at - started_at).total_seconds()
    elif started_at:
        duration_sec = (datetime.now(timezone.utc) - started_at).total_seconds()

    result_repr = None
    try:
        if job.get_status() == "failed":
            result_repr = "(job failed — see exception below)"
        else:
            result_repr = job.result
    except Exception as e:
        result_repr = f"(error reading result: {e})"

    exc_info = getattr(job, "exc_info", None) or ""

    def _safe_repr(obj, max_len=2000):
        try:
            s = repr(obj)
            return s[:max_len] + ("..." if len(s) > max_len else "")
        except Exception:
            return "(unable to repr)"

    job_data = {
        "id": job.get_id(),
        "state": job.get_status(),
        "type": job.meta.get("type"),
        "func_name": getattr(job, "func_name", None) or getattr(job, "origin", ""),
        "args": _safe_repr(getattr(job, "args", ())),
        "kwargs": _safe_repr(getattr(job, "kwargs", {})),
        "meta": job.meta,
        "created_at": created_at,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_sec": duration_sec,
        "result_repr": result_repr,
        "exc_info": exc_info,
    }
    return render_template("queue_job.html", job=job_data, not_found=False)


@app.route("/queue/clear_failed/", methods=["GET", "POST"])
def clear_failed():
    from rq_helpers import queue as q
    registry = q.failed_job_registry
    for job_id in registry.get_job_ids():
        try:
            registry.remove(job_id, delete_job=True)
        except Exception:
            pass
    return redirect("/queue/")


@app.route("/queue/clear_all/", methods=["GET", "POST"])
def clear_all():
    from rq_helpers import queue as q, get_all_job_ids
    for job_id in get_all_job_ids():
        job = q.fetch_job(job_id)
        if job:
            try:
                job.delete()
            except Exception:
                pass
    q.empty()
    return redirect("/queue/")


@app.route("/ctrl/", methods=["GET"])
def ctrl():
    return render_template(
        "ctrl.html",
        cfg=_ensure_redis_defaults(),
        bot_flags=_read_bot_yaml_flags(),
    )


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
    _ctrl_log(action, f"HTTP /ctrl/{action}/")
    return redirect('/ctrl/')


@app.route("/api/tags/add_tags_from_steps/", methods=["GET"])
def add_tags_from_steps():
    job = jobs.add_tags_from_steps.delay()
    inject_trace_context_into_job(job)
    return "ok"


@app.route("/api/tags/clean/", methods=["GET"])
def clean_tags():
    job = jobs.clean_tags.delay()
    inject_trace_context_into_job(job)
    return "ok"


@app.route("/api/tags/embeddings/", methods=["POST"])
@cross_origin()
def tags_embeddings():
    """spaCy vectors + similarity links for tag visualizations (en_core_web_md)."""
    try:
        body = request.get_json(silent=True) or {}
        words = body.get("words") or []
        if not isinstance(words, list):
            return jsonify({"ok": False, "error": "words must be a list"}), 400
        max_words = int(body.get("max_words", 48))
        max_words = max(4, min(max_words, 80))
        min_sim = float(body.get("min_sim", 0.38))
        min_sim = max(0.15, min(min_sim, 0.99))
        max_links = int(body.get("max_links", 160))
        max_links = max(8, min(max_links, 400))
        out = build_embeddings_response(
            words, max_words=max_words, min_sim=min_sim, max_links=max_links
        )
        return jsonify(out), 200
    except Exception as e:
        logger.exception("tags_embeddings failed")
        return jsonify({"ok": False, "error": str(e), "words": [], "vectors2d": [], "links": []}), 500


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
        data['struct_text'] = ""
        data['semantic'] = ""
        data['semantic_words'] = ""
        is_silent = data.get('silent') == '1'
        logger.info(f"step status {data['status_string']}{' (silent)' if is_silent else ''}")

        step_key = f"step:{data['number']}"
        partial_data = {
            'number': data['number'],
            'url': data.get('url', ''),
            'src': data.get('src', ''),
            'ip': data.get('ip', ''),
            'status_code': data.get('status_code', ''),
            'timestamp': data.get('timestamp', ''),
            'text': (data.get('text') or '')[:2048],
        }
        _save_to_step_hash(step_key, partial_data)

        if float(current_cfg.get('do_storage', 0)) == 1.0 and data.get('url'):
            try:
                requests.post(
                    f"{STORAGE_SERVICE_URL}/store",
                    json=partial_data, timeout=5,
                )
                logger.info(f"step: early storage OK for step {data['number']}")
            except Exception as e:
                logger.warning(f"step: early storage failed: {e}")

        if data['status_string'] == "ok":
            with step_span(step_number=data.get('number'), step_url=data.get('url')):
                set_step_span_attributes(
                    step_number=data.get('number'),
                    step_url=data.get('url'),
                )
                pending_jobs = []

                # PASS — semantic analysis via worker
                if float(current_cfg['do_pass']) == 1.0:
                    if not is_silent:
                        socketio.emit('step', data)
                    if len(data['text']) > 0:
                        job = enqueue_with_trace(queue, redis_connection, jobs.dostep, data, timeout=90, result_ttl=270)
                        _poll_job_and_emit(job, 'tags_updated', timeout=90, step_key=step_key, silent=is_silent)
                        pending_jobs.append(job)
                else:
                    if not is_silent:
                        socketio.emit('step', data)

                # GEO — fire-and-forget with background poll
                if float(current_cfg['do_geo']) == 1.0:
                    if not is_silent:
                        send_node_red_event(f"try {data.keys()}")
                    if "ip" in data.keys():
                        ip = data['ip']
                        if ip != "0":
                            job = enqueue_with_trace(queue, redis_connection, jobs.do_geo, ip, timeout=90, result_ttl=270)
                            _poll_job_and_emit(job, 'location', timeout=90, step_key=step_key, silent=is_silent)
                            pending_jobs.append(job)

                # ANALYZE — fire-and-forget with background poll
                if float(current_cfg['do_analyze']) == 1.0:
                    logger.info(f"step do_analyze")
                    html = data.get('html', data.get('text', ''))
                    job = enqueue_with_trace(
                        queue, redis_connection, jobs.analyze, html,
                        step_number=data.get('number'), step_url=data.get('url'),
                        timeout=90, result_ttl=270,
                    )
                    _poll_job_and_emit(job, 'analyzed', timeout=90, step_key=step_key, silent=is_silent)
                    pending_jobs.append(job)

                # SCREENSHOT — fire-and-forget with background poll
                if float(current_cfg['do_screenshot']) == 1.0:
                    if data.get('url'):
                        logger.info(f"step do_screenshot")
                        job = enqueue_with_trace(queue, redis_connection, jobs.do_screenshot, data, timeout=120, result_ttl=270)
                        _poll_job_and_emit(job, 'screenshot', timeout=120, step_key=step_key, silent=is_silent)
                        pending_jobs.append(job)

                # STORAGE updates happen incrementally via _poll_job_and_emit → _patch_storage
        else:
            logger.info(f"skip step actions")

    return "done"


@app.route("/api/analyze_all/", methods=['GET', 'POST'])
@cross_origin()
def analyze_all_proxy():
    if request.method == 'GET':
        text = request.args.get('text', '')
    else:
        data = request.get_json(silent=True) or {}
        text = data.get('text', '') or request.form.get('text', '')
    if not text:
        return jsonify({"error": "text parameter is required"}), 400
    try:
        url = f"{SEMANTIC_SERVICE_URL}/api/v1/semantic/analyze_all/"
        headers = {'content-type': 'application/json'}
        resp = requests.post(url, data=json.dumps({"text": text}), headers=headers, timeout=30)
        resp.raise_for_status()
        return jsonify(resp.json())
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Semantic service unavailable", "detail": str(e)}), 503


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
    _ctrl_log("restart", "HTTP /set_tick/")
    return redirect('/ctrl/')


@app.route("/add_analyze_job/", methods=['GET', 'POST'])
def add_analyze_job():
    if request.method == 'POST':
        data = request.form
        text = data['text']
        job = jobs.analyze.delay(text)
        inject_trace_context_into_job(job)
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
                        'noun_phrases': job.meta.get('noun_phrases'),
                        'sim': job.meta.get('sim'),
                    })
                else:
                    l.append({
                        'id': job.get_id(),
                        'type': job_type,
                    })
    return jsonify(l)


@app.route("/api/step/<step_num>/", methods=["GET"])
@cross_origin()
def api_step_detail(step_num):
    """Return the aggregated Redis hash for a single step."""
    result = _read_step_hash(f"step:{step_num}")
    if not result:
        return jsonify({"error": "step not found"}), 404
    return jsonify(result)


@app.route("/api/storage_step/<step_num>/", methods=["GET"])
@cross_origin()
def api_storage_step(step_num):
    """Proxy to storage-service GET /get/step/{number}."""
    try:
        resp = requests.get(
            f"{STORAGE_SERVICE_URL}/get/step/{step_num}", timeout=10)
        resp.raise_for_status()
        return jsonify(resp.json())
    except requests.exceptions.HTTPError:
        status = resp.status_code if resp is not None else 502
        return jsonify({"error": "step not found"}), status
    except Exception as e:
        logger.warning(f"api_storage_step: {e}")
        return jsonify({"error": str(e)}), 502


@app.route("/api/storage_latest/", methods=["GET"])
@cross_origin()
def api_storage_latest():
    """Proxy to storage-service GET /get/latest."""
    try:
        resp = requests.get(f"{STORAGE_SERVICE_URL}/get/latest", timeout=15)
        resp.raise_for_status()
        return jsonify(resp.json())
    except Exception as e:
        logger.warning(f"api_storage_latest: {e}")
        return jsonify({"error": str(e)}), 502


@app.route("/api/storage_ids/", methods=["GET"])
@cross_origin()
def api_storage_ids():
    """Proxy to storage-service GET /get/ids."""
    try:
        resp = requests.get(f"{STORAGE_SERVICE_URL}/get/ids", timeout=15)
        resp.raise_for_status()
        return jsonify(resp.json())
    except Exception as e:
        logger.warning(f"api_storage_ids: {e}")
        return jsonify({"error": str(e)}), 502


def _parse_geo_float(val):
    if val is None or val == "":
        return None
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return None


def _step_sort_key_storage_row(row):
    for key in ("id", "number"):
        v = row.get(key)
        if v is not None and str(v).strip() != "":
            try:
                return int(float(str(v)))
            except (ValueError, TypeError):
                pass
    return 0


@app.route("/api/storage_geo/", methods=["GET"])
@cross_origin()
def api_storage_geo():
    """
    Slim geo JSON for /geo/ globe.

    Response: { "data": [ { "number", "ip", "latitude", "longitude", "city" }, ... ] }
    Only rows with valid lat/lon (finite, in range, not both 0). Newest-first by id/number.
    Query: ?limit= (default 2000, max 5000).
    """
    limit = request.args.get("limit", default=2000, type=int)
    limit = max(1, min(limit, 5000))
    try:
        resp = requests.get(f"{STORAGE_SERVICE_URL}/get/latest", timeout=15)
        resp.raise_for_status()
        payload = resp.json()
        rows = payload.get("data") or []
    except Exception as e:
        logger.warning(f"api_storage_geo: {e}")
        return jsonify({"error": str(e)}), 502

    enriched = []
    for row in rows:
        lat = _parse_geo_float(row.get("latitude"))
        lon = _parse_geo_float(row.get("longitude"))
        if lat is None or lon is None:
            continue
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            continue
        if lat == 0.0 and lon == 0.0:
            continue
        enriched.append({
            "_k": _step_sort_key_storage_row(row),
            "number": str(row.get("number") or ""),
            "ip": str(row.get("ip") or ""),
            "latitude": lat,
            "longitude": lon,
            "city": str(row.get("city") or ""),
        })
    enriched.sort(key=lambda r: r["_k"], reverse=True)
    slim = [{k: v for k, v in r.items() if k != "_k"} for r in enriched[:limit]]
    return jsonify({"data": slim})


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
            socketio.emit('tags_updated')
            return jsonify(f"ok from POST {tag}" if body is None else {"ok": True, "tag": tag, "response": body})
        except requests.exceptions.RequestException as e:
            return jsonify({"error": "Tags service unreachable", "detail": str(e)}), 503


@app.route("/api/tags/add/", methods=["POST", "GET"])
@cross_origin()
def add_tags():
    if request.method == 'GET':
        tag = random.choice(RANDOM_TAG_WORDS)
        url = f"{TAGS_SERVICE_URL}/api/v1/tags/"
        headers = {'content-type': 'application/json'}
        data = {'name': tag, "count": 0}
        try:
            r = requests.post(url, data=json.dumps(data), headers=headers, timeout=15)
            body = _tags_response_json(r)
            if not r.ok:
                return jsonify({"error": "Tags service error", "status": r.status_code, "detail": body or r.text[:200]}), 502
            socketio.emit('tags_updated')
            return jsonify({"ok": True, "tag": tag, "response": body} if body is not None else {"ok": True, "tag": tag})
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
            socketio.emit('tags_updated')
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
                        'noun_phrases': job.meta.get('noun_phrases'),
                        'sim': job.meta.get('sim'),
                    })
    return jsonify(l)


@app.route("/add_wait_job/<num_iterations>", methods=["GET"])
def run_wait_job_get(num_iterations):
    job = jobs.wait.delay(int(num_iterations))
    inject_trace_context_into_job(job)
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
    _ctrl_log("start", "WebSocket")

@socketio.on('stop')
def handle_stop():
    _ctrl_log("stop", "WebSocket")

@socketio.on('restart')
def handle_restart():
    socketio.emit('clear')
    _ctrl_log("restart", "WebSocket")

@socketio.on('step')
def handle_step():
    _ctrl_log("step", "WebSocket")

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

@socketio.on('do_storage')
def handle_do_storage(value):
    redis.set('do_storage', float(value))

@socketio.on('sleep_time')
def handle_sleep_time(value):
    redis.set('sleep_time', float(value))


def _socket_bot_yaml_flag(key: str, value):
    try:
        b = bool(float(value))
        _write_bot_yaml_flags({key: b})
        logger.info("bot.yaml %s=%s (socketio)", key, b)
    except Exception as e:
        logger.exception("bot.yaml %s update failed: %s", key, e)


@socketio.on('bot_send_events')
def handle_bot_send_events(value):
    _socket_bot_yaml_flag("send_events", value)


@socketio.on('bot_send_sublinks')
def handle_bot_send_sublinks(value):
    _socket_bot_yaml_flag("send_sublinks", value)


@socketio.on('bot_log_events')
def handle_bot_log_events(value):
    _socket_bot_yaml_flag("log_events", value)


@socketio.event
def my_ping():
    socketio.emit('my_pong')


# =========================================================================
#  Entry point
# =========================================================================

if __name__ == '__main__':
    print("start flask 2.2.0")
    socketio.run(app, host='0.0.0.0', allow_unsafe_werkzeug=True, debug=True)
