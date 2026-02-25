#
#   project/server/main/tasks.py
#
import os
import sys
import time
import json
import glob
import logging
import re

import requests
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.rq import RqIntegration
from rq.decorators import job
from rq import get_current_job
from rq_helpers import redis_connection


ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

TAGS_SERVICE_URL = os.getenv('TAGS_SERVICE_URL', 'http://tags_service:8000')
SEMANTIC_SERVICE_URL = os.getenv('SEMANTIC_SERVICE_URL', 'http://semantic_service:8005')
STORAGE_SERVICE_URL = os.getenv('STORAGE_SERVICE_URL', 'http://storage_service:7781')
IP_SERVICE_URL = os.getenv('IP_SERVICE_URL', 'http://bots.arthew0.online:8004')
RENDERER_SERVICE_URL = os.getenv('RENDERER_SERVICE_URL', 'http://html-renderer-service:3000')
SVC_NAME = os.getenv("SVC_NAME", "jobs service")

# S3 configuration
S3_HOST = os.getenv('S3_HOST', 's3.firstvds.ru')
S3_PORT = os.getenv('S3_PORT', '443')
S3_ACCESS_KEY = os.getenv('S3_ACCESS_KEY', '')
S3_SECRET_KEY = os.getenv('S3_SECRET_KEY', '')
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'steps')

SENTRY_DSN = os.getenv('SENTRY_DSN', '')

def _traces_sampler(ctx):
    return 1.0


if SENTRY_DSN and not sentry_sdk.is_initialized():
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

logging.basicConfig(
    level=logging.DEBUG,
    format=f'[{SVC_NAME}] %(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)
logger.info(f"Sentry initialized for environment: {ENVIRONMENT}" if SENTRY_DSN else "Sentry not configured")  



def remove_html_tags(text):
    clean_text = re.sub(r'<.*?>', '', text)
    return clean_text

def remove_special_characters(text):
    # Remove non-ASCII characters (keeping basic ASCII only)
    clean_text = re.sub(r'[^\x00-\x7F]+', '', text)
    # Remove control characters except space, keeping letters, numbers, basic punctuation
    clean_text = re.sub(r'[\x00-\x1F\x7F-\x9F]', ' ', clean_text)
    # Remove special symbols that might cause issues (keeping periods, commas, hyphens, underscores)
    clean_text = re.sub(r'[^\w\s.,\-]', '', clean_text)
    # Remove newlines, tabs, and carriage returns
    clean_text = clean_text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    # Collapse multiple spaces into single space
    clean_text = re.sub(r'\s+', ' ', clean_text)
    # Remove leading/trailing whitespace
    clean_text = clean_text.strip()
    return clean_text


@job('default', connection=redis_connection, timeout=600, result_ttl=600)
def clean_tags():
    self_job = get_current_job()
    self_job.meta['type'] = "clean_tags"
    self_job.save_meta()

    with sentry_sdk.start_span(op="http.client", description="tags_service get grouped"):
        url_short = f"{TAGS_SERVICE_URL}/api/v1/tags/tags/group/"
        response = requests.get(url_short, timeout=30)
        r = response.json()

    with sentry_sdk.start_span(op="http.client", description="tags_service delete grouped") as span:
        span.set_data("count", len(r))
        for i, t in enumerate(r):
            idd = t['id']
            urld = f"{TAGS_SERVICE_URL}/api/v1/tags/{idd}/"
            requests.delete(urld, timeout=15)
            time.sleep(.001)
            if i % 50 == 0:
                self_job = get_current_job()
                self_job.meta['progress'] = {
                    'num_iterations': len(r),
                    'iteration': i,
                    'percent': i / max(len(r), 1) * 100
                }
                self_job.save_meta()

    with sentry_sdk.start_span(op="http.client", description="tags_service get all"):
        url = f"{TAGS_SERVICE_URL}/api/v1/tags/"
        response = requests.get(url, timeout=30)
        r = response.json()

    with sentry_sdk.start_span(op="http.client", description="tags_service delete all") as span:
        span.set_data("count", len(r))
        for i, t in enumerate(r):
            idd = t['id']
            urld = f"{TAGS_SERVICE_URL}/api/v1/tags/{idd}/"
            requests.delete(urld, timeout=15)
            time.sleep(.001)
            if i % 50 == 0:
                self_job = get_current_job()
                self_job.meta['progress'] = {
                    'num_iterations': len(r),
                    'iteration': i,
                    'percent': i / max(len(r), 1) * 100
                }
                self_job.save_meta()

    from datetime import datetime
    now = datetime.now()
    date_time = now.strftime("%Y-%m-%d_%H-%M-%S")    
    return date_time


@job('default', connection=redis_connection, timeout=90, result_ttl=90)
def add_tags(tags):
    results = []
    for word in tags:
        tag_name = str(word)[0:50]
        url = f"{TAGS_SERVICE_URL}/api/v1/tags/"
        headers = {'content-type': 'application/json'}
        data = {'name': tag_name, "count": 0}
        response = requests.post(url, data=json.dumps(data), headers=headers, timeout=15)
        results.append(response.json())
    return results



@job('default', connection=redis_connection, timeout=900, result_ttl=900)
def add_tags_from_steps():
    MAX_STEPS = 80000
    self_job = get_current_job()
    self_job.meta['type'] = "add_tags_from_steps"
    self_job.save_meta()

    with sentry_sdk.start_span(op="fs", description="read step files"):
        files = sorted(glob.glob("data/path/steps/*"))
        files_txt = sorted(glob.glob("data/path/txt/*"))

    num_iterations = min(len(files), MAX_STEPS)
    for i, file in enumerate(files[0:MAX_STEPS]):
        contents = open(file).readlines()
        step = int(contents[0].strip())
        text = open(files_txt[step-1]).read().strip().replace("\n", "")
        
        with sentry_sdk.start_span(op="http.client", description=f"semantic+tags step {step}"):
            url_semantic = f"{SEMANTIC_SERVICE_URL}/api/v1/semantic/tags/"
            headers = {'content-type': 'application/json'}
            rr = requests.post(url_semantic, data=json.dumps({"text": text}), headers=headers, timeout=30)
            sem_data = rr.json()
            sim = sem_data.get('sim', [])

            for hras in sim:
                url = f"{TAGS_SERVICE_URL}/api/v1/tags/"
                headers = {'content-type': 'application/json'}
                tag_data = {'name': hras, "count": 0}
                requests.post(url, data=json.dumps(tag_data), headers=headers, timeout=15)
        
        if i % 50 == 0:
            self_job = get_current_job()
            self_job.meta['step'] = step
            self_job.meta['type'] = "active"
            self_job.meta['progress'] = {
                'num_iterations': num_iterations,
                'iteration': i,
                'percent': 100 * i / max(num_iterations, 1)
            }
            self_job.save_meta()

        if i >= MAX_STEPS:
            return text


#
#
#  1. STEP
#   
@job('default', connection=redis_connection, timeout=90, result_ttl=270)
def dostep(step):

    logger.info(f"job dostep step {step}")
        
    self_job = get_current_job()
    self_job.meta['type'] = "step"
    if "current_url" in step.keys():
        self_job.meta['url'] = step['current_url']

    ip = step.get('ip', '0.0.0.0')
    self_job.meta['ip'] = ip
    text = step.get('text', '')
    self_job.meta['text'] = text
    self_job.save_meta()

    with sentry_sdk.start_span(op="parse", description="clean text"):
        text = remove_html_tags(text)
        text = remove_special_characters(text)

    tags = []
    words = []
    hrases = []
        
    if len(text) > 128:
        with sentry_sdk.start_span(op="http.client", description="semantic_service /tags/"):
            url_semantic = f"{SEMANTIC_SERVICE_URL}/api/v1/semantic/tags/"
            headers = {'content-type': 'application/json'}
            rr = requests.post(url_semantic, data=json.dumps({"text": text}), headers=headers, timeout=30)
            sem_data = rr.json()
            sentry_sdk.logger.info(f"semantic_service data: {sem_data}")
            sim = sem_data.get('sim', [])
            words = sim

        with sentry_sdk.start_span(op="http.client", description="tags_service add tags") as span:
            span.set_data("tags_count", len(sim))
            for hras in sim:
                url = f"{TAGS_SERVICE_URL}/api/v1/tags/"
                headers = {'content-type': 'application/json'}
                tag_data = {'name': hras, "count": 0}
                response = requests.post(url, data=json.dumps(tag_data), headers=headers, timeout=15)

    do_save = float(redis_connection.get('do_save') or 0)
    if do_save == 1.0:
        with sentry_sdk.start_span(op="http.client", description="storage_service /store"):
            sentry_sdk.logger.info(f"semantic_service write {step['step']} to store")
            url = f"{STORAGE_SERVICE_URL}/store"
            headers = {'content-type': 'application/json'}
            step['text'] = text
            step_number_val = step.pop('step', None)
            step.pop('headers', None)
            step.pop('src_url', None)
            step.pop('current_url', None)
            try:
                response = requests.post(url, data=json.dumps(step), headers=headers, timeout=30)
                r = response.json()
            except Exception as e:
                logger.warning(f"Storage service error: {e}")
                r = {"error": str(e)}
            if step_number_val is not None:
                step['step'] = step_number_val
    else:
        logger.info("do_save disabled, skipping storage write")

    self_job.meta['progress'] = {
        "tags": tags,
        "semantic": tags,
        "semantic_words": words,
        "semantic_hrases": hrases,
        "text": text[0:1024] + "...",
        'num_iterations': 4,
        'iteration': 4,
        'percent': 100
    }    
    self_job.save_meta()

    return_obj = {
            "step": step['number'],
            "code": step['status_code'], 
            "ip": ip, 
            "url": step['url'],
            "src_url": step['src'],
            "tags": tags,
            "semantic": tags,
            "semantic_words": words,
            "semantic_hrases": hrases,
            "text": text[0:1024] + "..."
        }

    return return_obj










#
#
#  GEO
#   
@job('default', connection=redis_connection, timeout=90, result_ttl=270)
def do_geo(ip):

    logger.info(f"job do_geo ip {ip}")
    
    self_job = get_current_job()    
    self_job.meta['type'] = "geo"        
    self_job.meta['ip'] = ip
    self_job.save_meta()
    
    location = {'ip': ip, 'city': '', 'latitude': 0, 'longitude': 0, 'error': ''}

    with sentry_sdk.start_span(op="http.client", description="ip_service geo lookup") as span:
        span.set_data("ip", ip)
        try:
            url = f"{IP_SERVICE_URL}/api/v1/ip/{ip}/"
            headers = {'content-type': 'application/json'}
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            geo = response.json()

            location['city'] = geo.get('city', '')
            location['latitude'] = geo.get('latitude', 0)
            location['longitude'] = geo.get('longitude', 0)
            location['error'] = geo.get('error', '')

        except Exception as e:
            location['error'] = str(e)
            logger.warning(f"do_geo failed for {ip}: {e}")

    self_job.meta['progress'] = {'num_iterations': 2, 'iteration': 2, 'percent': 100}
    self_job.save_meta()
       
    return location




#
#
#   SAVE
#   
@job('default', connection=redis_connection, timeout=90, result_ttl=90)
def save(data):

    logger.info(f"job save data {data}")

    url = data['current_url']
    step = data['step']
    text = data['text']
    filename = f'data/txt/{step.zfill(4)}.txt'
    
    self_job = get_current_job()    
    self_job.meta['type'] = "save"
    self_job.meta['url'] = url
    self_job.meta['filename'] = filename
    self_job.save_meta()
        
    if len(text) > 0:
        with sentry_sdk.start_span(op="fs", description="write text/html/headers"):
            with open(filename, 'w') as file:
                file.write(text)

            with open(f'data/txt/{step.zfill(4)}.html', 'w') as file:
                file.write(data['html'])

            with open(f'data/txt/{step.zfill(4)}_headers.txt', 'w') as file:
                file.write(data['current_url']+"\n")
                file.write(data['ip']+"\n")            
                file.write(data['headers'])

    self_job.meta['progress'] = {'num_iterations': 2, 'iteration': 2, 'percent': 100}
    self_job.save_meta()
    
    return filename





#
#
#   ANALYZE
#
@job('default', connection=redis_connection, timeout=90, result_ttl=270)
def analyze(html):
    """Analyze HTML content using spaCy NER."""
    self_job = get_current_job()
    self_job.meta['type'] = "analyze"
    self_job.save_meta()

    with sentry_sdk.start_span(op="parse", description="clean html"):
        text = remove_html_tags(html)
        text = remove_special_characters(text)

    entities = []
    with sentry_sdk.start_span(op="ml", description="spacy NER") as span:
        span.set_data("text_length", len(text))
        try:
            import spacy
            nlp = spacy.load("en_core_web_sm")
            doc = nlp(text[:100000])
            entities = [{"text": ent.text, "label": ent.label_} for ent in doc.ents]
            span.set_data("entities_count", len(entities))
        except Exception as e:
            sentry_sdk.logger.warning(f"analyze error: {e}")

    tags = []
    words = []
    hrases = []
        
    if len(text) > 128:
        with sentry_sdk.start_span(op="http.client", description="semantic_service /tags/"):
            url_semantic = f"{SEMANTIC_SERVICE_URL}/api/v1/semantic/tags/"
            headers = {'content-type': 'application/json'}
            rr = requests.post(url_semantic, data=json.dumps({"text": text}), headers=headers, timeout=30)
            sem_data = rr.json()
            sentry_sdk.logger.info(f"semantic_service data: {sem_data}")
            sim = sem_data.get('sim', [])
            words = sim
            tags = words
            hrases = words

        with sentry_sdk.start_span(op="http.client", description="tags_service add tags") as span:
            span.set_data("tags_count", len(tags))
            for tagg in tags:
                url = f"{TAGS_SERVICE_URL}/api/v1/tags/"
                headers = {'content-type': 'application/json'}
                tag_data = {'name': tagg, "count": 0}
                response = requests.post(url, data=json.dumps(tag_data), headers=headers, timeout=15)

    self_job = get_current_job()
    self_job.meta['tags'] = tags
    self_job.meta['words'] = words
    self_job.meta['hrases'] = hrases
    self_job.meta['progress'] = {'num_iterations': 2, 'iteration': 2, 'percent': 100}
    self_job.save_meta()

    return {
        "tags": tags,
        "words": words,
        "hrases": hrases,
        "entities": entities,
        "text_length": len(text),
    }


def _filenamify(url):
    """Convert a URL into a safe filename."""
    import re as _re
    # Remove protocol
    name = _re.sub(r'^https?://', '', url)
    # Replace unsafe characters with hyphens
    name = _re.sub(r'[^a-zA-Z0-9._-]', '-', name)
    # Collapse multiple hyphens
    name = _re.sub(r'-+', '-', name)
    # Trim leading/trailing hyphens
    name = name.strip('-')
    # Limit length
    if len(name) > 200:
        name = name[:200]
    return name


def _get_s3_client():
    """Create a boto3 S3 client for the configured endpoint."""
    import boto3
    endpoint_url = f"https://{S3_HOST}:{S3_PORT}" if S3_PORT != '443' else f"https://{S3_HOST}"
    return boto3.client(
        's3',
        endpoint_url=endpoint_url,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
    )


@job('default', connection=redis_connection, timeout=120, result_ttl=270)
def do_screenshot(data):
    """
    1. Render a screenshot of the current step URL via html-renderer-service
    2. Generate a filename from the URL with filenamify
    3. Upload the PNG to S3
    4. Return the public URL
    """
    logger.info(f"job do_screenshot start")

    self_job = get_current_job()
    self_job.meta['type'] = "screenshot"
    self_job.save_meta()

    current_url = data.get('current_url', data.get('url', ''))
    step_number = data.get('step', data.get('number', '0'))

    with sentry_sdk.start_span(op="http.client", description="html-renderer render") as span:
        span.set_data("url", current_url)
        render_url = f"{RENDERER_SERVICE_URL}/render"
        params = {
            'url': current_url,
            'width': 1080/2,
            'height': 1920/2,
            'format': 'jpeg',
            'quality': 80,
            'dsf': '1',
            'json_on_error': 'true',
        }
        response = requests.get(render_url, params=params, timeout=60)
        # При ошибке рендеринга сервис возвращает 200 + JSON {"error": "..."}
        if response.headers.get('content-type', '').startswith('application/json'):
            try:
                data = response.json()
                if 'error' in data:
                    logger.warning(f"do_screenshot: renderer error for {current_url}: {data['error']}")
                    return {
                        'step': step_number,
                        'url': current_url,
                        'error': data['error'],
                    }
            except Exception:
                pass
        response.raise_for_status()
        image_bytes = response.content
        span.set_data("image_size", len(image_bytes))

    with sentry_sdk.start_span(op="s3", description="s3 upload screenshot") as span:
        safe_name = _filenamify(current_url)
        s3_key = f"screenshots/{str(step_number).zfill(8)}-{safe_name}.jpg"
        span.set_data("s3_key", s3_key)
        s3 = _get_s3_client()
        s3.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=image_bytes,
            ContentType='image/jpeg',
            ACL='public-read',
        )

    public_url = f"https://{S3_HOST}/{S3_BUCKET_NAME}/{s3_key}"

    self_job = get_current_job()
    self_job.meta['screenshot_url'] = public_url
    self_job.meta['progress'] = {'num_iterations': 3, 'iteration': 3, 'percent': 100}
    self_job.save_meta()

    sentry_sdk.logger.info(f"screenshot uploaded: {public_url}")

    return {
        'step': step_number,
        'url': current_url,
        'screenshot_url': public_url,
        's3_key': s3_key,
    }




# the timeout parameter specifies how long a job may take
# to execute before it is aborted and regardes as failed
# the result_ttl parameter specifies how long (in seconds)
# successful jobs and their results are kept.
# for more detail: https://python-rq.org/docs/jobs/
# 7*24*60*60
@job('default', connection=redis_connection, timeout=90, result_ttl=90)
def wait(num_iterations):
    """
    wait for num_iterations seconds
    """
    # get a reference to the job we are currently in
    # to send back status reports
    self_job = get_current_job()
    self_job.meta['type'] = "wait"
    self_job.save_meta()
    print(f"start job {self_job}")

    # define job
    for i in range(1, num_iterations + 1):  # start from 1 to get round numbers in the progress information
        time.sleep(1)
        self_job.meta['progress'] = {
            'num_iterations': num_iterations,
            'iteration': i,
            'percent': i / num_iterations * 100
        }
        # save meta information to queue
        self_job.save_meta()

    # return job result (can be accesed as job.result)
    print(f"finish job {self_job}")
    
    from datetime import datetime
    import random
    now = datetime.now()
    date_time = now.strftime("%Y-%m-%d_%H-%M-%S")
    
    return date_time
    # return {"one":"hello", "two":7}


@job('default', connection=redis_connection, timeout=900, result_ttl=900)
def clean_tsv_data():
    """
    Clean the data.tsv file by removing unsupported characters and line breaks
    """
    self_job = get_current_job()
    self_job.meta['type'] = "cleaning"
    self_job.save_meta()
    
    input_file = "data/data.tsv"
    output_file = "data/data_cleaned.tsv"
    backup_file = "data/data_backup.tsv"
    
    try:
        # Read the file
        with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        cleaned_lines = []
        
        for i, line in enumerate(lines):
            # Remove line breaks within the line content
            clean_line = line.replace('\n', ' ').replace('\r', ' ')
            
            # Split by tabs to get individual fields
            fields = clean_line.split('\t')
            
            # Clean each field
            cleaned_fields = []
            for field in fields:
                # Remove special characters that might cause issues
                field = remove_special_characters(field)
                # Replace multiple spaces with single space
                field = ' '.join(field.split())
                cleaned_fields.append(field)
            
            # Rejoin with tabs and add newline at end
            cleaned_line = '\t'.join(cleaned_fields) + '\n'
            cleaned_lines.append(cleaned_line)
            
            # Update progress
            if i % 100 == 0:
                self_job = get_current_job()
                self_job.meta['progress'] = {
                    'num_iterations': total_lines,
                    'iteration': i,
                    'percent': i / total_lines * 100
                }
                self_job.save_meta()
        
        # Create backup of original file
        import shutil
        shutil.copy2(input_file, backup_file)
        
        # Write cleaned data to output file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.writelines(cleaned_lines)
        
        # Replace original with cleaned version
        shutil.move(output_file, input_file)
        
        self_job = get_current_job()
        self_job.meta['type'] = "completed"
        self_job.meta['progress'] = {
            'num_iterations': total_lines,
            'iteration': total_lines,
            'percent': 100
        }
        self_job.save_meta()
        
        return {
            "status": "success",
            "total_lines": total_lines,
            "cleaned_lines": len(cleaned_lines),
            "backup_file": backup_file
        }
        
    except Exception as e:
        self_job = get_current_job()
        self_job.meta['type'] = "error"
        self_job.meta['error'] = str(e)
        self_job.save_meta()
        return {
            "status": "error",
            "error": str(e)
        }


@job('default', connection=redis_connection, timeout=1)
def add(x, y):
    return x + y


@job('default', connection=redis_connection, timeout=1)
def pulse():
    print("job pulse")
    return True
