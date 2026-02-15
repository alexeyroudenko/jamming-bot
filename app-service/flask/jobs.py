#
#   project/server/main/tasks.py
#
from rq.decorators import job
from rq import get_current_job
from rq_helpers import redis_connection
import time
import json
import requests
import glob
import logging
import sys


import os
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
import logging


ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

TAGS_SERVICE_URL = os.getenv('TAGS_SERVICE_URL', 'http://tags_service:8000')
SEMANTIC_SERVICE_URL = os.getenv('SEMANTIC_SERVICE_URL', 'http://semantic_service:8005')
STORAGE_SERVICE_URL = os.getenv('STORAGE_SERVICE_URL', 'http://storage_service:7781')
IP_SERVICE_URL = os.getenv('IP_SERVICE_URL', 'http://bots.arthew0.online:8004')
RENDERER_SERVICE_URL = os.getenv('RENDERER_SERVICE_URL', 'http://html-renderer-service')
SVC_NAME = os.getenv("SVC_NAME", "jobs service")

# S3 configuration
S3_HOST = os.getenv('S3_HOST', 's3.firstvds.ru')
S3_PORT = os.getenv('S3_PORT', '443')
S3_ACCESS_KEY = os.getenv('S3_ACCESS_KEY', '')
S3_SECRET_KEY = os.getenv('S3_SECRET_KEY', '')
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'steps')

SENTRY_DSN = "https://74f2e249c0ff771f90f0f69560153ed0@o4508353081573376.ingest.de.sentry.io/4508353103003728"

if SENTRY_DSN:
    logging_integration = LoggingIntegration(
        level=logging.DEBUG,
        event_level=logging.INFO
    )
    
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            logging_integration,
        ],
        enable_logs=True,
        environment=ENVIRONMENT,
        traces_sample_rate=1.0,
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



import re
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


import requests

@job('default', connection=redis_connection, timeout=600, result_ttl=600)
def clean_tags():
    self_job = get_current_job()
    self_job.meta['type'] = "wait"
    self_job.save_meta()
    num_iterations = 2000
    
    url_short = f"{TAGS_SERVICE_URL}/api/v1/tags/tags/group/"
    response = requests.get(url_short)
    
    self_job = get_current_job() 
    self_job.meta['type'] = "responced"
    self_job.save_meta()
    
    r = response.json()
    
    self_job = get_current_job() 
    self_job.meta['type'] = "parsed"
    self_job.meta['data'] = r
    self_job.save_meta()
    
    num_iterations = len(r)
    
    self_job = get_current_job() 
    self_job.meta['type'] = "begining"
    self_job.save_meta()
    
    for i, t in enumerate(r):
        self_job = get_current_job() 
        self_job.meta['type'] = "active"
        idd = t['id']
        urld = f"{TAGS_SERVICE_URL}/api/v1/tags/{idd}/"
        r = requests.delete(urld)
        time.sleep(.001)
        self_job.meta['progress'] = {
            'num_iterations': num_iterations,
            'iteration': i,
            'percent': i / num_iterations * 100
        }
        self_job.save_meta()
    
    url = f"{TAGS_SERVICE_URL}/api/v1/tags/"
    response = requests.get(url)
    r = response.json()
    num_iterations = len(r)
    for i, t in enumerate(r):
        idd = t['id']
        urld = f"{TAGS_SERVICE_URL}/api/v1/tags/{idd}/"
        r = requests.delete(urld)
        time.sleep(.001)
        self_job = get_current_job() 
        self_job.meta['progress'] = {
            'num_iterations': num_iterations,
            'iteration': i,
            'percent': i / num_iterations * 100
        }
        self_job.save_meta()
        
    
    from datetime import datetime
    now = datetime.now()
    date_time = now.strftime("%Y-%m-%d_%H-%M-%S")    
    return date_time


@job('default', connection=redis_connection, timeout=90, result_ttl=90)
def add_tags(tags):
    tags = {}
    for w in tags:
        print(f"tags: {w}")
        tags = w[0:50]        
        import json
        import requests
        url = f"{TAGS_SERVICE_URL}/api/v1/tags/"
        headers = {'content-type': 'application/json'}
        data = {'name': tags, "count": 0}
        response = requests.post(url, data=json.dumps(data), headers=headers)
        tags = response.json()



@job('default', connection=redis_connection, timeout=900, result_ttl=900)
def add_tags_from_steps():
    MAX_STEPS = 80000
    self_job = get_current_job()
    self_job.meta['type'] = "wait"
    self_job.save_meta()
    
    files = sorted(glob.glob("data/path/steps/*"))
    files_txt = sorted(glob.glob("data/path/txt/*"))

    self_job = get_current_job()
    self_job.meta['type'] = "starting"
    self_job.save_meta()
        
    num_iterations = MAX_STEPS
    i = 0
    for file in files[0:MAX_STEPS]:        
        contents = open(file).readlines()
        step = int(contents[0].strip())         
        # step = i + 1   
        # print(file, step)   
        text_path = files_txt[step]     
        text = open(files_txt[step-1]).read().strip().replace("\n","")
        
        url_semantic = f"{SEMANTIC_SERVICE_URL}/api/v1/semantic/tags/"
        headers = {'content-type': 'application/json'}
        rr = requests.post(url_semantic, data = json.dumps({"text": text}), headers=headers)                
        data = rr.json()
        if "sim" in data.keys(): 
            sim = rr.json()['sim']
        
        for hras in sim:       
            url = f"{TAGS_SERVICE_URL}/api/v1/tags/"
            headers = {'content-type': 'application/json'}
            data = {'name': hras, "count": 0}
            response = requests.post(url, data=json.dumps(data), headers=headers)
        
        self_job = get_current_job()
        self_job.meta['step'] = step
        self_job.meta['type'] = "active"
        self_job.meta['progress'] = {
            'num_iterations': num_iterations,
            'iteration': i,
            'percent': 100 * i / num_iterations
        }
        self_job.save_meta()
        i += 1
        
        if i > MAX_STEPS:
            return text
            
            # break


#
#
#  1. STEP
#   
@job('default', connection=redis_connection, timeout=90, result_ttl=120)
def dostep(step): 
        
    self_job = get_current_job()
    self_job.meta['progress'] = {
        'num_iterations': 4,
        'iteration': 1,
        'percent': 25
    }

    self_job.meta['type'] = "step"
    if "current_url" in step.keys():
        self_job.meta['url'] = step['current_url']

    ip = "0.0.0.0" 
    if "ip" in step.keys():
        ip = step['ip']
    self_job.meta['ip'] = ip
        
    text = "" 
    if "text" in step.keys():
        text = step['text']
    self_job.meta['text'] = text
    
    self_job.save_meta()
        
    self_job.meta['progress'] = {
        'num_iterations': 4,
        'iteration': 2,
        'percent': 50
    }
    self_job.save_meta()
    
    
    text = remove_html_tags(text)
    text = remove_special_characters(text)
    
    print(text)    

    tags = []
    words = []
    hrases = []
        
    if len(text) > 128:
        # semantic analyze 1
        #
        # import json
        # import requests
        # url = "http://spacyapi/ent"
        # headers = {'content-type': 'application/json'}
        # d = {'text': text , 'model': 'en_core_web_md'}
        # response = requests.post(url, data=json.dumps(d), headers=headers)
        # r = response.json()
        # print(r)
        # # Always define hrases as a list, even if ents is missing or empty
        # hrases = []
        # if isinstance(r, dict):
        #     hrases = [ent["text"] for ent in r.get("ents", []) if "text" in ent]
        # elif isinstance(r, list):
        #     hrases = [ent["text"] for ent in r if isinstance(ent, dict) and "text" in ent]
        # print("hrases:", hrases)
        

        # semantic analyze 2
        # 
        import json
        import requests                       
        url_semantic = f"{SEMANTIC_SERVICE_URL}/api/v1/semantic/tags/"
        headers = {'content-type': 'application/json'}
        rr = requests.post(url_semantic, data = json.dumps({"text": text}), headers=headers)                
        data = rr.json()
        sentry_sdk.logger.info(f"semantic_service data: {data}")
        if "sim" in data.keys(): 
            sim = rr.json()['sim']
        
        for hras in sim:       
            url = f"{TAGS_SERVICE_URL}/api/v1/tags/"
            headers = {'content-type': 'application/json'}
            data = {'name': hras, "count": 0}
            response = requests.post(url, data=json.dumps(data), headers=headers)
            words = sim
        
    self_job.meta['progress'] = {
        'num_iterations': 4,
        'iteration': 3,
        'percent': 100
    }    
    self_job.save_meta()
    
    
    #
    # Calculate cloud
    #
    # print(f"category: {category}")
    # tags = {}
    # if category != "Undefined topic":

    # for w in words:
    #     print(f"word: {w}")
    #     if len(w) > 4:
    #         word = w[0:50]
    #         import json
    #         import requests
    #         url = f"{TAGS_SERVICE_URL}/api/v1/tags/"
    #         headers = {'content-type': 'application/json'}
    #         data = {'name': word, "count": 0}
    #         response = requests.post(url, data=json.dumps(data), headers=headers)
    #         tags = response.json()


    sentry_sdk.logger.info(f"semantic_service write {step['step']} to store")
    #
    # write to file
    #
    import json
    import requests
    url = f"{STORAGE_SERVICE_URL}/store"
    headers = {'content-type': 'application/json'}
    step['text'] 
    step['text'] = text    
    del step['headers'] 
    del step['src_url']
    del step['current_url'] 
    del step['step']
    response = requests.post(url, data=json.dumps(step), headers=headers)
    try:
        r = response.json()
    except Exception:
        r = {"raw": response.text}





    self_job.meta['progress'] = {
        "tags": tags,
        "semantic": tags,
        "semantic_words": words,
        "semantic_hrases": hrases,
        "text":text[0:1024] + "...",
        'num_iterations': 4,
        'iteration': 4,
        'percent': 100
    }    
    self_job.save_meta()

    from sentry_sdk import metrics
    metrics.count("step", step['number'])
    
    # metrics.count("step.failed", 0)
    # metrics.count("step.timeout", 0)
    # metrics.count("step.error", 0)
    # metrics.count("step.canceled", 0)
    # metrics.count("step.pending", 0)
    # metrics.count("step.running", 0)
    # metrics.count("step.completed", 0)
    # metrics.count("step.failed", 0)


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
            "text":text[0:1024] + "..."
        }

    return return_obj










#
#
#  GEO
#   
@job('default', connection=redis_connection, timeout=90, result_ttl=270)
def do_geo(ip):
    
    self_job = get_current_job()    
    self_job.meta['progress'] = {
        'num_iterations': 2,
        'iteration': 1,
        'percent': 50
    }                
    self_job.meta['type'] = "geo"        
    self_job.meta['ip'] = ip
    self_job.save_meta()
    
    location = {}
    location['ip'] = ip
    location['city'] = ""
    location['latitude'] = 0
    location['longitude'] = 0
    location['error'] = ""
    try:

        import json
        import requests
        url = f"{IP_SERVICE_URL}/api/v1/ip/{ip}/"
        headers = {'content-type': 'application/json'}
        data = {'ip': ip}
        response = requests.get(url, headers=headers)
        geo = response.json()

        location['city'] = geo['city']
        location['latitude'] = geo['latitude']
        location['longitude'] = geo['longitude']
        location['error'] = geo['error']
        
    except Exception as e:
        error = str(e)
    
    self_job = get_current_job()    
    self_job.meta['progress'] = {
        'num_iterations': 2,
        'iteration': 2,
        'percent': 100
    }            
    self_job.meta['type'] = "geo"        
    self_job.meta['ip'] = ip
    self_job.save_meta()
       
    return location




#
#
#   SAVE
#   
@job('default', connection=redis_connection, timeout=90, result_ttl=90)
def save(data):

    url = data['current_url']
    step = data['step']
    text = data['text']
    filename = f'data/txt/{step.zfill(4)}.txt'
    
    self_job = get_current_job()    
    self_job.meta['type'] = "save"
    self_job.meta['step'] = data
    self_job.meta['progress'] = {
        'num_iterations': 2,
        'iteration': 0,
        'percent':100
    }
    self_job.meta['url'] = url
    self_job.meta['filename'] = filename
    self_job.save_meta()
        
    if len(text) > 0:
        with open(filename, 'w') as file:
            file.write(text)

        with open(f'data/txt/{step.zfill(4)}.html', 'w') as file:
            file.write(data['html'])

        with open(f'data/txt/{step.zfill(4)}_headers.txt', 'w') as file:
            file.write(data['current_url']+"\n")
            file.write(data['ip']+"\n")            
            file.write(data['headers'])

    self_job = get_current_job()    
    self_job.meta['type'] = "save"
    self_job.meta['step'] = data
    self_job.meta['progress'] = {
        'num_iterations': 2,
        'iteration': 2,
        'percent':100
    }
    self_job.meta['url'] = url
    self_job.meta['filename'] = filename
    self_job.save_meta()
    
    return filename





#
#
#   ANALYZE
#
@job('default', connection=redis_connection, timeout=90, result_ttl=120)
def analyze(html):
    """Analyze HTML content using spaCy NER."""
    self_job = get_current_job()
    self_job.meta['type'] = "analyze"
    self_job.meta['progress'] = {
        'num_iterations': 2,
        'iteration': 1,
        'percent': 50
    }
    self_job.save_meta()

    text = remove_html_tags(html)
    text = remove_special_characters(text)

    entities = []
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(text[:100000])  # limit to 100k chars
        entities = [{"text": ent.text, "label": ent.label_} for ent in doc.ents]
    except Exception as e:
        sentry_sdk.logger.warning(f"analyze error: {e}")

    self_job = get_current_job()
    self_job.meta['type'] = "analyze"
    self_job.meta['progress'] = {
        'num_iterations': 2,
        'iteration': 2,
        'percent': 100
    }
    self_job.save_meta()

    return {
        "entities": entities,
        "text_length": len(text),
    }


# #
# #
# #   
# @job('default', connection=redis_connection, timeout=90, result_ttl=90)
# def screenshot(data):
    
#     step = data['step']  
#     current_url = data['current_url']
#     out_filename = f'data/txt/{step.zfill(4)}.jpg'
#     img_url = f"http://192.168.31.18:8080/screenshot?url={current_url}&viewport-width=1024&viewport-height=1024"
#     import requests
#     response = requests.get(img_url)
#     if response.status_code == 200:
#         with open(out_filename, 'wb') as f:
#             f.write(response.content)
            
#     self_job = get_current_job()
#     self_job.meta['progress'] = {
#         'num_iterations': 1,
#         'iteration': 1,
#         'percent':100,
#         'type': "screenshot"
#     }
#     self_job.meta['type'] = "screenshot"
#     self_job.save_meta()
    
#     return out_filename


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
    self_job = get_current_job()
    self_job.meta['type'] = "screenshot"
    self_job.meta['progress'] = {
        'num_iterations': 3,
        'iteration': 1,
        'percent': 33
    }
    self_job.save_meta()

    sentry_sdk.logger.info(f"do_screenshot start")
    sentry_sdk.logger.info(f"data {data}")
    
    current_url = data.get('current_url', data.get('url', ''))
    step_number = data.get('step', data.get('number', '0'))

    sentry_sdk.logger.info(f"data {step_number}")
    sentry_sdk.logger.info(f"current_url {current_url}")

    # 1. Render screenshot via html-renderer-service
    render_url = f"{RENDERER_SERVICE_URL}/render"
    params = {
        'url': current_url,
        'width': 1280,
        'height': 720,
        'format': 'png',
    }
    response = requests.get(render_url, params=params, timeout=90)
    sentry_sdk.logger.info(f"do_screenshot response {response}")
    response.raise_for_status()
    image_bytes = response.content

    sentry_sdk.logger.info(f"do_screenshot image_bytes {image_bytes}")
    sentry_sdk.logger.info(f"do_screenshot image_bytes length {len(image_bytes)}")

    time.sleep(1)

    self_job = get_current_job()
    self_job.meta['progress'] = {
        'num_iterations': 3,
        'iteration': 2,
        'percent': 66
    }
    sentry_sdk.logger.info(f"do_screenshot progress {self_job.meta['progress']}")
    self_job.save_meta()

    # 2. Generate filename from URL
    safe_name = _filenamify(current_url)
    s3_key = f"screenshots/{step_number}-{safe_name}.png"
    sentry_sdk.logger.info(f"do_screenshot s3_key {s3_key}")
    # 3. Upload to S3
    s3 = _get_s3_client()
    s3.put_object(
        Bucket=S3_BUCKET_NAME,
        Key=s3_key,
        Body=image_bytes,
        ContentType='image/png',
        ACL='public-read',
    )

    # Build public URL
    public_url = f"https://{S3_HOST}/{S3_BUCKET_NAME}/{s3_key}"

    self_job = get_current_job()
    self_job.meta['type'] = "screenshot"
    self_job.meta['screenshot_url'] = public_url
    self_job.meta['progress'] = {
        'num_iterations': 3,
        'iteration': 3,
        'percent': 100
    }
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
