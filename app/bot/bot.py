#!/home/pi/jamming_bot/.venv/bin/python
import os
import sys
import csv
from datetime import datetime
import time
from urllib.parse import urlparse
import traceback
import requests
from bs4 import BeautifulSoup
from databases import Database
import asyncio

import json

from tld import get_tld
import validators
import signal
import time

import logging, sys
import yaml
from yaml.loader import SafeLoader

from pythonosc import udp_client

import tldextract

config_file = "bot.yaml"

STEP_URL = "http://flask:5000/bot/step/"
EVENT_URL = "http://flask:5000/bot/events"
SUBLINK_URL = "http://flask:5000/bot/sublink/add/"

import sentry_sdk
sentry_sdk.init(
    dsn=os.getenv('SHHH_SENTRY_URL'),
    traces_sample_rate=1.0,
)

def slow_function():
    import time
    time.sleep(0.1)
    return "done"

def fast_function():
    import time
    time.sleep(0.05)
    return "done"

# Manually call start_profiler and stop_profiler
# to profile the code in between
sentry_sdk.profiler.start_profiler()
for i in range(0, 10):
    slow_function()
    fast_function()
#
# Calls to stop_profiler are optional - if you don't stop the profiler, it will keep profiling
# your application until the process exits or stop_profiler is called.
sentry_sdk.profiler.stop_profiler()



exclude_tlds = {
    "ru", "cn", "es", "mx", "ar", "pt", "br", "kr", "jp", "de", "fr", "it", "in", "id", "ph",
    "tr", "th", "vn", "gr", "pl", "ua", "by", "kz", "ir", "pk", "eg", "sa", "ae", "il", "ma",
    "ng", "za", "ke", "tz", "co", "cl", "pe", "ve", "uy", "bo", "ec", "cr", "gt", "hn", "ni",
    "sv", "py", "do", "cu", "hk", "tw", "my", "lk", "bd"
}
def domain_is_en(domain):
    tld = tldextract.extract(domain).suffix
    return tld not in exclude_tlds
        

def get_second_level_domain(url):
    extracted = tldextract.extract(url)
    # Second-level domain is the combination of the domain and the suffix
    second_level_domain = f"{extracted.domain}.{extracted.suffix}"
    return second_level_domain

class GracefulKiller:
  kill_now = False
  def __init__(self):
    signal.signal(signal.SIGINT, self.exit_gracefully)
    signal.signal(signal.SIGTERM, self.exit_gracefully)

  def exit_gracefully(self,signum, frame):
    self.kill_now = True


class UrlsFilter():
    """UrlsFilter big sites
       TODO: add big sites automaticaly
    """
    def __init__(self):
        self.filters = []
        self.init_data()

    def clean_url(self, url):
        return url.replace("www.", "")

    def get_values(self, url):
        hostname = urlparse(url).hostname
        data = {"hostname": hostname, "url": url, "visited":0}
        # logging.debug(f"get values {hostname} {url} {data}")
        return data

    def init_data(self):
        filename = 'top500Domains.csv'
        logging.info(f"init_data {filename}")
        with open(filename, newline='') as csv_file:
            spamreader = csv.reader(csv_file, delimiter=',', quotechar='\"')
            for row in spamreader:
                self.filters.append(self.clean_url(''.join(row[1])))
                self.filters.append("mailto")



class NetSpider():
    """NetSpider my spider
       TODO: add sites screenshots
    """
    def __init__(self, sleep_time, osc_address, resolve_coords, count_per_domain = 20):
        self.is_active = False
        self.filter = UrlsFilter()
        self.sleep_time = sleep_time
        self.step_number = 0        
        self.count_errors = 0
        self.resolve_coords = resolve_coords
        self.count_per_domain = count_per_domain
        self.do_verbs = False
        self.send_events = False
        self.send_osc = False
        self.send_sublinks = False
        self.resume_at_restart = False

        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()

        logging.info(f"my ip {ip}")
        logging.info(f"osc address ip {osc_address}")
        #mask = [0,0,0,255]
        #broadcast = [(ioctet | ~moctet) & 0xff for ioctet, moctet in zip(ip, mask)]
        #print(broadcast)

        self.osc = udp_client.SimpleUDPClient(osc_address, 7001)
        pass
    
    '''
        Control realtime
    '''
    def reload_config(self):
        with open(config_file) as file:
            config = yaml.load(file, Loader=SafeLoader)                
            self.sleep_time = config['sleep_time']
            self.send_events = config['send_events']
            self.send_osc = config['send_osc']
            self.send_sublinks = config['send_sublinks']
            self.resume_at_restart = config['resume_at_restart']
            #self.is_active = config['is_active']

    '''
        Init database
    '''
    async def init_db(self):
        logging.info("init_db")
        now = datetime.now()
        date_time = now.strftime("%Y-%m-%d_%H-%M-%S")
        self.db_name = f"db_{date_time}.db"
        self.db_name = "database.db"
        resume = self.resume_at_restart and os.path.exists(self.db_name)
        if not resume:
            try:
                os.remove(self.db_name)
            except FileNotFoundError:
                logging.info("db not exist")
        else:
            logging.info("resume db")
            
        self.database = Database(f'sqlite+aiosqlite:///{self.db_name}')
        await self.database.connect()
        if not resume:
            logging.info("create new db")
            query = """CREATE TABLE Urls (id INTEGER PRIMARY KEY, hostname VARCHAR(127), url VARCHAR(127) unique, src_url VARCHAR(127), visited INTEGER)"""
            await self.database.execute(query=query)
        else:
            query = """SELECT count(*) FROM Urls WHERE visited=1"""
            count_res = await self.database.fetch_one(query=query)
            logging.info(f"resume db from {count_res} {count_res[0]}")
            count = int(count_res[0])
            logging.info(f"resume db from {count}")
            self.step_number = count


    async def set_visited(self, url):
        logging.info("set_visited", url)
        try:
            values = self.filter.get_values(url)
            query = "INSERT INTO Urls(hostname, url, visited) VALUES (:hostname, :url, :visited)"
            await self.database.execute(query=query, values=values)
        except Exception as e:
            print("Exception set_visited:", e)
            pass
    
    async def insert(self, url, src_url):
        #logging.info(f"insert {url}")
        try:
            #logging.info(f"self.filter {self.filter}")
            values = self.filter.get_values(url)
            values['src_url'] = src_url            
            #logging.info(f"insert values to db {url}")
            query = "INSERT INTO Urls(hostname, url, src_url, visited) VALUES (:hostname, :url, :src_url, :visited)"
            await self.database.execute(query=query, values=values)
        except Exception as e:
            logging.error(f"Exception insert {traceback.print_exc()}")
            pass
        
    async def retrieve_stored_links_for_domain(self, current_base_domain):
        query = f"SELECT * FROM Urls where hostname='{current_base_domain}'" 
        # logging.info(f"{query}")
        rows = await self.database.fetch_all(query=query)
        stored_lnks = []
        for row in rows:
            stored_lnks.append(row[2])
        return stored_lnks


    



    '''
        notify step
    '''                        
    def notify_about_step(self, step_data):
        if self.send_events:
            try:
                r = requests.post(STEP_URL, data = step_data)            
                # logging.info(f"url: {STEP_URL}")
            except Exception as e0:
                logging.error(f"error send step data {STEP_URL}")
                self.send_events = False
            
        if self.send_osc:
            step_data_osc = [step_data['step'], step_data['current_url'], step_data['src_url']]
            try:   
                self.osc.send_message("/step", step_data_osc)
            except Exception as e0:
                logging.error(f"error send OSC: {e0} {step_data.items()}")


    '''
        notify event
    '''                            
    def notify_about_eventp(self, event_name, data):
        if self.send_events:
            try:
                url = EVENT_URL + f"/{event_name}/"
                r = requests.post(url, {"data":data})
                # logging.info(f"url: {url}")
            except Exception as e0:
                logging.error(f"error send eventp data {url}")
                self.send_events = False
        if self.send_osc:            
            try:
                self.osc.send_message(f"/events/{event_name}/", [])
            except Exception as e0:
                logging.error(f"error send OSC: {e0}")
                

    '''    
        notify sublinks
    '''                            
    def notify_about_sublink(self, data):
        if self.send_sublinks:      
            try:      
                r = requests.post(SUBLINK_URL, data)
            except Exception as e0:
                logging.error(f"error send sublink data {SUBLINK_URL}")
                self.send_sublinks = False
            
            
            
            
            
            
            
            
    '''
    
    
        collect_links 
    ''' 
    async def collect_links(self, link_elements, current_site, current_url, current_base_domain):

        '''
            already added link for current domain
        '''              
        stored_links_for_domain = await self.retrieve_stored_links_for_domain(current_base_domain)
                                
        import mimetypes
        
        for link_element in link_elements:
            
            url = link_element['href']
            href = link_element['href'] 

            # url = link_element
            # href = link_element

            mimetype = mimetypes.guess_type(url)
                                    
            if mimetype[0] == "text/html" or mimetype[0] == None:
                new_link_element = ""
                if not "javascript" in url and not "mailto" in url:
                    new_hostname = urlparse(url).hostname
                    if not new_hostname:
                        full_url = requests.compat.urljoin(current_site, url)
                        url = self.filter.clean_url(full_url)
                        
                    if not new_hostname: 
                        new_link_element = self.filter.get_values(full_url)['url']
                    else:
                        if self.filter.clean_url(new_hostname) in self.filter.filters:
                            #logging.debug(f"skip href {href} because host {new_hostname}")
                            ...
                        else:   
                            new_link_element = href
                                                                                    
                if new_link_element not in stored_links_for_domain and new_link_element != "" and domain_is_en(new_link_element):
                    
                    hostname = get_second_level_domain(new_link_element)
                    stored_links_for_domain = await self.retrieve_stored_links_for_domain(hostname)
                    count_stored_links_for_domain = len(stored_links_for_domain)
                    count_elements = count_stored_links_for_domain
                    if count_elements > self.count_per_domain:
                        logging.debug(f"skip add")
                    else:

                        #
                        # add url to database
                        #
                        values = self.filter.get_values(href)
                        values['url'] = new_link_element
                        values['src_url'] = current_url                                                                                            
                        values['hostname'] = hostname
                        
                        # logging.info(f"add to queue {values}")                                                                                                                    
                        try:
                            self.notify_about_sublink({"hostname":hostname,"src_url":current_url,"url":new_link_element})
                        except:
                            ...
                                                                                                                
                        query = "INSERT OR IGNORE INTO Urls(hostname, url, src_url, visited) VALUES (:hostname, :url, :src_url, :visited)"
                        await self.database.execute(query=query, values=values)        
        

    #
    #
    #   Step
    #
    async def step(self):
        #logging.info(f"self.step {str(self.step_number)}")
        self.step_number = self.step_number + 1

        try:
            
            #
            #  Calc next step retrieve_next_url()
            #  
            #
            #

            self.notify_about_eventp("retrieve_next_url", self.step_number)

            #
            query = "SELECT id, hostname, url, src_url, count(visited) FROM Urls where visited==0 GROUP BY hostname ORDER BY count(visited) LIMIT 1"
            rows = await self.database.fetch_all(query=query)            
            url_id = rows[0][0]
            # domain = get_second_level_domain(rows[0][1])
            current_url = rows[0][2]
            src_url = rows[0][3]
            
            #
            #  Set visited
            #
            self.notify_about_eventp("set_visited", url_id)
            #
            query = f"UPDATE Urls SET visited=1 WHERE id={url_id}"
            await self.database.execute(query=query)
            
            
            #
            #   Validate URL
            # 
            self.notify_about_eventp("validate_url", current_url)
            #             
            current_site = urlparse(current_url).scheme + "://" + urlparse(current_url).netloc
            valid = validators.url(current_site)
                        
            if valid:
                
                import tld 
                try:
                    res = get_tld(current_url, as_object=True)
                except tld.exceptions.TldBadUrl: 
                    logging.warning(f"step {self.step_number} \t ERR \t {current_base_domain} \t {src_url} > {current_url} \t bad url")
                    self.notify_about_eventp("error_retrieve_url", {})                    
                    step_data = { "step":self.step_number, "src_url": src_url, "current_url": current_url} 
                    step_data["status_code"] = "000"
                    self.notify_about_step(step_data)
                    return
                
                except tld.exceptions.TldDomainNotFound:
                    logging.warning(f"step {self.step_number} \t ERR \t {current_base_domain} \t {src_url} > {current_url} \t domain not found")
                    self.notify_about_eventp("error_retrieve_url", {})                    
                    step_data = {"step":self.step_number, "src_url": src_url, "current_url": current_url} 
                    step_data["status_code"] = "000"
                    self.notify_about_step(step_data)
                    return

                current_base_domain = res.fld
                current_base_domain = get_second_level_domain(current_base_domain)
                
                try:
                    
                    #
                    #
                    #       Retrieve page
                    #
                    #
                    self.notify_about_eventp("retrieve_page", current_url)
                    #
                    logging.debug(f"start load  {current_url}")
                    
                    step_data = {"step":self.step_number, 
                            "src_url": src_url, 
                            "current_url": current_url,
                            "status_code": 0,
                            "headers": {},
                            "link_elements": len({}),
                            "ip":0,
                            "text":""}
                    
                    response = requests.get(current_url,
                                            headers={
                                                    'Accept-Language': 'en-US, en;q=0.5',
                                                    'Accept-Charset':  'utf-8',
                                                },
                                            timeout=10, 
                                            stream=True)                    
                    ip = response.raw._connection.sock.getpeername()
                        
                    
                    headers_dump = json.dumps(dict(response.headers))                    
                    #logging.info(f"headers: {headers_dump}")
                    
                    self.notify_about_eventp("headers", headers_dump)
                    
                    text = ""
                    link_elements = []
                    
                    step_data = {"step":self.step_number, 
                            "src_url": src_url, 
                            "current_url": current_url,
                            "status_code": response.status_code,
                            "headers": headers_dump,
                            "link_elements": len(link_elements),
                            "ip":ip,
                            "text":""}
                    
                    content_type = str(response.headers.get("Content-Type", "").lower())
                    
                    if "html" not in content_type:
                        
                        logging.warning(f"step {self.step_number} \t {current_url} \t bad content-type: {content_type}")                        
                        self.notify_about_eventp("step_error_content", content_type)                        
                        self.notify_about_step(step_data)
                    
                    elif response.status_code != 200 :
                        logging.warning(f"step {self.step_number} \t {response.status_code} \t {current_base_domain} \t {src_url} > {current_url} \t {ip}")                                                
                        self.notify_about_eventp("step_error_status", response.status_code)                        
                        self.notify_about_step(step_data)
                        
                    else:
                        
                        #
                        #
                        #
                        self.notify_about_eventp("analyze_page_fix_codepage", response.encoding)
                        #
                        # if response.encoding != 'utf-8':
                        #     response.encoding = 'utf-8'
                        # html_content = response.text                        
                        html_content = response.content.decode('utf-8')
                        
                        # #
                        # #
                        # #    Analyze page
                        # #
                        # self.notify_about_eventp("analyze_page_fast_link_coollect", content_type)
                        
                        # import re
                        # def extract_links_fast(html):
                        #     return set(re.findall(r'href=["\'](https?://[^\s"\'<>]+)', html))                        
                        # link_elements = extract_links_fast(html_content)
                        
                        # logging.info(f"link_elements {link_elements}")


                        #
                        #
                        #   Get Text
                        #
                        self.notify_about_eventp("analyze_page_fast_text_exxtract", content_type)
                        import re
                        def extract_text_re(html_content):
                            return re.sub(r'<[^>]+>', '', html_content)                        
                        
                        def remove_css_text_re(html_content):
                            return re.sub(r'(?s)<style>(.*?)<\/style>', '', html_content)                        

                        text = remove_css_text_re(extract_text_re(html_content))

                        # logging.debug(f"start parse {current_url}")  
                        soup = BeautifulSoup(response.content, "html.parser", from_encoding="utf-8")                         
                        self.notify_about_eventp("analyze_page_remove_nav", content_type) 
                        
                        
                        # Remove navigation text
                        for tag in soup(['button', 'nav', 'footer', 'header', 'aside']):
                            tag.decompose()                            
                        
                        
                        # self.notify_about_eventp("analyze_page_collect_stripped_strings", content_type) 
                        # page_text = []
                        # for element in soup.stripped_strings:
                        #     if len(element) > 20:
                        #         page_text.append(element)                                                
                        # text = ' '.join(page_text)                                                                        
                        
                        #
                        #
                        self.notify_about_eventp("analyze_page_collect_links_elements", content_type) 
                        #
                        link_elements = soup.select("a[href]")
                        
                        self.notify_about_eventp("analyze_page_finish", content_type)
                        
                        logging.info(f"step {self.step_number} \t {response.status_code} \t {current_base_domain} \t {src_url} > {current_url} \t {len(link_elements)} \t {ip}")
                        
                        
                        
                        
                        #
                        #
                        #       Collect links
                        #
                        self.notify_about_eventp("collect_links", link_elements)
                        #  
                        await self.collect_links(link_elements, 
                                           current_site, 
                                           current_url, 
                                           current_base_domain)
                        
                        
                        #
                        #
                        #       Say finish
                        #
                        self.notify_about_eventp("say_finish", len(link_elements))
                        #
                        step_data['text'] = text
                        step_data['html'] = response.content                        
                        step_data['link_elements'] = len(link_elements)
                        self.notify_about_step(step_data)


                except Exception as e1:
                    logging.warning(f"step {self.step_number} \t ERR \t {current_base_domain} \t {src_url} > {current_url} \t e1 line {e1.__traceback__.tb_lineno}")
                    self.notify_about_eventp("error_retrieve_url", {})                    
                    step_data = {
                        "step":self.step_number, 
                        "src_url": src_url, 
                        "current_url": current_url,
                        "status_code": "000"
                    } 
                    # self.notify_about_step(step_data)
                    
        except Exception as e2:
            self.count_errors += 1
            logging.error(f"Exception step 2 {e2} line:{e2.__traceback__.tb_lineno}")
            print(f"Exception in step 2: {e2}", traceback.print_exc())
            # if self.count_errors > 10000:
            #     logging.error(f"Exception self.count_errors {self.count_errors} .... finish")
            #     self.stop()
            #     exit()

    """
        Controls
    """
    async def start(self, start_url, src_url):
        
        await self.init_db()
        if not self.resume_at_restart:
            await self.insert(start_url, src_url)
            self.step_number = 0
            logging.info(f"start with {start_url}")
            
        try:
            self.osc.send_message("/start", {})
        except Exception as e0:
            logging.error(f"error send OSC: {e0}")

    def stop(self):
        try:
            self.osc.send_message("/stop", {})
        except Exception as e0:
            logging.error(f"error send OSC: {e0}")
        pass

    def reset(self):
        pass



async def main():
    
    #
    # Init app
    #
    
    with open(config_file) as file:
        config = yaml.load(file, Loader=SafeLoader)
        
    STEP_URL = config["step_url"]
    EVENT_URL = config["event_url"]
    SUBLINK_URL = config["sublink_url"]
    
    logging.info(f"init bot version: {config['version']}")
    
    if config['receive_events']:        
        from redis import Redis
        redis = Redis(host='redis', port=6379)        
        pubsub = redis.pubsub()
        CHANNEL_NAME = 'ctrl'
        pubsub.subscribe(CHANNEL_NAME)
    
    killer = GracefulKiller()
    
    spider = NetSpider(config['sleep_time'], 
                       config['osc_adress'], 
                       config['resolve_coords'], 
                       count_per_domain = config['count_per_domain'])
    spider.resume_at_restart = config['resume_at_restart']
    spider.is_active = config['is_active']
    
    
    from omegaconf import OmegaConf
    from osc_server import OSCServer
    osc_config = OmegaConf.load("osc_server.yml")
    osc_server = OSCServer(osc_config)
    osc_server.run_osc_reciver()
    
    #feature_states = self.osc_feature_controler.feature_states
    
    await spider.start(config['start_url'], config['src_url'])
    
    
        
    try:
        
        #
        # Main loop
        #        
        while True:
            
            #
            # CTRL from REDIS
            #
            try:
                                
                if config['receive_events']:
                    message = pubsub.get_message()                                    
                    if message:                                        
                        logging.info(f"message {message} - {message["data"]}")
                          
                        if message["data"] == 1:                        
                            logging.error(f"skip {message["data"]}")
                        else:                    
                            data = json.loads(message["data"])                                                    
                            logging.info(f"message {data}")
                                                    
                            if data == "start":
                                logging.info("start") 
                                spider.is_active = True
                                
                            if data == "stop":
                                logging.info("stop") 
                                spider.is_active = False
                                
                            if data == "step":                                
                                await spider.step()
                                    
                            if data == "restart":
                                logging.info(f"restart") 
                                await spider.start(config['start_url'], config['src_url'])


            except Exception as e:
                logging.error(f"main loop {e}")

            #
            # Automative 
            #
            if spider.is_active:
                await spider.step()
            
            # else:
            #     logging.info("iddle")
                                          
            spider.reload_config()
            STEP_URL = config["step_url"]
            EVENT_URL = config["event_url"]
            SUBLINK_URL = config["sublink_url"]
            
            time.sleep(spider.sleep_time)
            time.sleep(0.01)
            
            if killer.kill_now:
                osc_server.stop_osc_receiver()
                break
            
    except KeyboardInterrupt as ex:
        osc_server.stop_osc_receiver()
        print('goodbye!')




if __name__ == '__main__':

    # now = datetime.now()
    # date_time = now.strftime("%Y-%m-%d_%H-%M-%S")
    # log_file_name = f"db_{date_time}.log"
    # log_file_name = f"db.log"
    
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
                        handlers=[
                            # logging.FileHandler(log_file_name),
                            logging.StreamHandler(sys.stdout)
                        ],
                        # filemode='a',
                        encoding='utf-8',
                        level=logging.INFO,
                        datefmt='%Y-%m-%d %H:%M:%S')
    

    asyncio.run(main())