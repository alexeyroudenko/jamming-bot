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


import re
def remove_html_tags(text):
    clean_text = re.sub(r'<.*?>', '', text)
    return clean_text

def remove_special_characters(text):
    # Remove non-ASCII characters
    clean_text = re.sub(r'[^\x00-\x7F]+', '', text)
    # Remove special characters except letters, numbers, and whitespace
    clean_text = re.sub(r'[^a-zA-Z0-9\s]', '', clean_text)
    # Remove newlines and tabs
    clean_text = clean_text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    return clean_text


import requests

@job('default', connection=redis_connection, timeout=600, result_ttl=600)
def clean_tags():
    self_job = get_current_job()
    self_job.meta['type'] = "wait"
    self_job.save_meta()
    num_iterations = 2000
    
    url_short = "http://tags_service:8000/api/v1/tags/tags/group/"
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
        urld = f"http://tags_service:8000/api/v1/tags/{idd}/"
        r = requests.delete(urld)
        time.sleep(.001)
        self_job.meta['progress'] = {
            'num_iterations': num_iterations,
            'iteration': i,
            'percent': i / num_iterations * 100
        }
        self_job.save_meta()
    
    url = "http://tags_service:8000/api/v1/tags/"
    response = requests.get(url)
    r = response.json()
    num_iterations = len(r)
    for i, t in enumerate(r):
        idd = t['id']
        urld = f"http://tags_service:8000/api/v1/tags/{idd}/"
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
        url = "http://tags_service:8000/api/v1/tags/"
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
        
        url_semantic = f"http://semantic_service:8005/api/v1/semantic/tags/"
        headers = {'content-type': 'application/json'}
        rr = requests.post(url_semantic, data = json.dumps({"text": text}), headers=headers)                
        data = rr.json()
        if "sim" in data.keys(): 
            sim = rr.json()['sim']
        
        for hras in sim:       
            url = "http://tags_service:8000/api/v1/tags/"
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
        url_semantic = f"http://semantic_service:8005/api/v1/semantic/tags/"
        headers = {'content-type': 'application/json'}
        rr = requests.post(url_semantic, data = json.dumps({"text": text}), headers=headers)                
        data = rr.json()
        if "sim" in data.keys(): 
            sim = rr.json()['sim']
        
        # for hras in sim:       
        #     url = "http://tags_service:8000/api/v1/tags/"
        #     headers = {'content-type': 'application/json'}
        #     data = {'name': hras, "count": 0}
        #     response = requests.post(url, data=json.dumps(data), headers=headers)

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

    for w in words:
        print(f"word: {w}")
        if len(w) > 4:
            word = w[0:50]
            import json
            import requests
            url = "http://tags_service:8000/api/v1/tags/"
            headers = {'content-type': 'application/json'}
            data = {'name': word, "count": 0}
            response = requests.post(url, data=json.dumps(data), headers=headers)
            tags = response.json()


    #
    # write to file
    #
    import json
    import requests
    url = "http://storage_service:7781/store"
    headers = {'content-type': 'application/json'}
    step['text'] 
    step['text'] = text    
    del step['headers'] 
    del step['src_url']
    del step['current_url'] 
    del step['step']
    response = requests.post(url, data=json.dumps(step), headers=headers)
    r = response.json()





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
        url = f"http://bots.arthew0.online:8004/api/v1/ip/{ip}/"
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
#   
@job('default', connection=redis_connection, timeout=90, result_ttl=90)
def screenshot(data):
    
    step = data['step']  
    current_url = data['current_url']
    out_filename = f'data/txt/{step.zfill(4)}.jpg'
    img_url = f"http://192.168.31.18:8080/screenshot?url={current_url}&viewport-width=1024&viewport-height=1024"
    import requests
    response = requests.get(img_url)
    if response.status_code == 200:
        with open(out_filename, 'wb') as f:
            f.write(response.content)
            
    self_job = get_current_job()
    self_job.meta['progress'] = {
        'num_iterations': 1,
        'iteration': 1,
        'percent':100,
        'type': "screenshot"
    }
    self_job.meta['type'] = "screenshot"
    self_job.save_meta()
    
    return out_filename






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


@job('default', connection=redis_connection, timeout=1)
def add(x, y):
    return x + y    

@job('default', connection=redis_connection, timeout=1)
def pulse():
    print("job pulse")
    return True