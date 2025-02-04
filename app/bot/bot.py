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

from tld import get_tld
import validators
import signal
import time

import logging, sys
import yaml
from yaml.loader import SafeLoader

from pythonosc import udp_client

import tldextract

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
        logging.debug(f"get values {hostname} {url} {data}")
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
        self.filter = UrlsFilter()
        self.sleep_time = sleep_time
        self.step_number = 0
        self.is_active = True
        self.count_errors = 0
        self.resolve_coords = resolve_coords
        self.count_per_domain = count_per_domain
        self.do_verbs = False

        # pip install -U spacy
        # python -m spacy download en_core_web_sm
        import spacy
        self.nlp = spacy.load("en_core_web_sm")

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

        self.osc = udp_client.SimpleUDPClient(osc_address, 8000)
        pass

    async def create_db(self):
        logging.info("create_db")
        now = datetime.now()
        date_time = now.strftime("%Y-%m-%d_%H-%M-%S")
        self.db_name = f"db_{date_time}.db"
        self.db_name = "database.db"
        os.remove(self.db_name)
        resume = False        
        if os.path.exists(self.db_name):
            resume = True
            logging.info("resume db")
            #os.remove(self.db_name)
        self.database = Database(f'sqlite+aiosqlite:///{self.db_name}')
        await self.database.connect()
        if not resume:
            logging.info("create new db")
            query = """CREATE TABLE Urls (id INTEGER PRIMARY KEY, hostname VARCHAR(127), url VARCHAR(127) unique, src_url VARCHAR(127), visited INTEGER)"""
            await self.database.execute(query=query)

    async def set_visited(self, url):
        logging.info("set_visited", url)
        try:
            values = self.filter.get_values(url)
            query = "INSERT INTO Urls(hostname, url, visited) VALUES (:hostname, :url, :visited)"
            await self.database.execute(query=query, values=values)
        except Exception as e:
            print("Exception set_visited:", e)
            pass
    
    async def insert(self, url):
        logging.info(f"insert {url}")
        try:
            logging.info(f"self.filter {self.filter}")
            values = self.filter.get_values(url)
            logging.info(f"values {url}")
            query = "INSERT INTO Urls(hostname, url, visited) VALUES (:hostname, :url, :visited)"
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


    async def step(self):
        #logging.debug(f"self.step {str(self.step_number)}")
        self.step_number = self.step_number + 1
        query = "SELECT id, hostname, url, src_url, count(visited) FROM Urls where visited==0 GROUP BY hostname ORDER BY count(visited) LIMIT 1"        
        rows = await self.database.fetch_all(query=query)
        try:
            url_id = rows[0][0]
            domain = get_second_level_domain(rows[0][1])
            current_url = rows[0][2]
            src_url = rows[0][3]
            query = f"UPDATE Urls SET visited=1 WHERE id={url_id}"
            await self.database.execute(query=query)
            
            # current_domain = urlparse(current_url).hostname
            current_site = urlparse(current_url).scheme + "://" + urlparse(current_url).netloc
            valid = validators.url(current_site)
            
            # id , hostname, current_url unique, src_url
            #logging.debug(f"try id:{url_id} hostname:{hostname} \t target:{current_url} \tsrc: {src_url} \t  valid:{valid}")

            if valid:
                res = get_tld(current_url, as_object=True)
                current_base_domain = res.fld
                current_base_domain = get_second_level_domain(current_base_domain)                            
                
                try:
                    response = requests.get(current_url, timeout=1, stream=True)
                    ip, port = response.raw._connection.sock.getpeername()                    
                    soup = BeautifulSoup(response.content, "html.parser", from_encoding="utf-8")                    
                    text = soup.get_text(" ", strip=True)
                    
                    
                    # logging.info(f"text {text}")
                    
                    if self.do_verbs:
                        doc = self.nlp(text)
                        print("Verbs:", [token.lemma_ for token in doc if token.pos_ == "VERB"])

                    link_elements = soup.select("a[href]")
                    
                    import random
                    random.shuffle(link_elements)
                    
                    logging.info(f"step {self.step_number} \t {current_base_domain} \t {src_url} > {current_url} \t {len(link_elements)} \t {ip}")
                    
                    data = [self.step_number, src_url, current_url, len(link_elements), ip, text]
                    rdata = {"step":self.step_number, "src_url":src_url, "current_url":current_url, "link_elements":len(link_elements), "ip":ip, "text":text}
                    
                    #
                    #
                    #
                    url = f'http://10.0.0.10:5000/bot/step/'
                    r = requests.post(url, data = rdata)



                    
                    if self.resolve_coords:
                        if self.step_number > 1:
                            try:
                                from ip2geotools.databases.noncommercial import DbIpCity
                                response = DbIpCity.get(ip, api_key='free')
                                # logging.info(f"response {response}") 
                                data.append(response.latitude)
                                data.append(response.longitude)
                                data.append(response.city)
                            except Exception as e:
                                pass
                                # logging.error(f"Error retrieve coords {e}")
                    
                    # try:
                    #     self.osc.send_message("/step", data)
                    # except Exception as e0:
                    #     logging.error(f"error send OSC: {e0}")                    
                    # Retrieve count stored links for domain
                                        
                    stored_links_for_domain = await self.retrieve_stored_links_for_domain(current_base_domain)
                    
                    for link_element in link_elements:
                        
                        url = link_element['href']
                        href = link_element['href']
                                                
                        new_link_element = ""
                        if not "javascript" in url and not "mailto" in url:
                            new_hostname = urlparse(url).hostname
                            # new_hostname = get_second_level_domain(new_hostname)
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
                                                                                               
                        # logging.info(f"new_link_element {new_link_element}")
                                                
                        if new_link_element not in stored_links_for_domain and new_link_element != "":
                            
                            hostname = get_second_level_domain(new_link_element)
                            
                            # check count links for domain in db
                            stored_links_for_domain = await self.retrieve_stored_links_for_domain(hostname)
                            logging.debug(f"hostname {hostname} -- {stored_links_for_domain}")                    
                            count_stored_links_for_domain = len(stored_links_for_domain)
                            count_elements = count_stored_links_for_domain
                            logging.debug(f"{count_elements} ? {self.count_per_domain}")
                            
                            if count_elements > self.count_per_domain:
                                logging.debug(f"skip add")
                            else:
                                # add url to database
                                values = self.filter.get_values(href)
                                values['url'] = new_link_element
                                values['src_url'] = current_url                                                                                            
                                values['hostname'] = hostname
                                logging.debug(f"add new_link_element {new_link_element} because host {hostname} \t values{values}")
                                query = "INSERT OR IGNORE INTO Urls(hostname, url, src_url, visited) VALUES (:hostname, :url, :src_url, :visited)"
                                await self.database.execute(query=query, values=values)


                except Exception as e1:
                    logging.error(f"Exception step 1 {e1}")
                    # print("Exception in step 1:", e1, traceback.print_exc())
                    pass

        except Exception as e2:
            self.count_errors += 1
            logging.error(f"Exception step 2 {e2}")
            # print(f"Exception in step 2: {rows}", e2, traceback.print_exc())
            if self.count_errors > 10000:
                logging.error(f"Exception self.count_errors {self.count_errors} .... finish")
                self.stop()
                exit()
            pass

    """
    Controls
    """
    async def start(self, start_url):
        logging.info(f"start with {start_url}")
        await self.create_db()
        await self.insert(start_url)
        self.step_number = 0
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
    config_file = "bot.yaml"
    with open(config_file) as file:
        config = yaml.load(file, Loader=SafeLoader)
    
    if config['color_log']:
        logger = logging.getLogger()
        import coloredlogs 
        coloredlogs.install(level="INFO", logger=logger)
        coloredlogs.install(fmt='%(asctime)s %(name)s[%(process)d] %(levelname)s %(message)s')

    killer = GracefulKiller()
    spider = NetSpider(config['sleep_time'], 
                       config['osc_adress'], 
                       config['resolve_coords'], 
                       count_per_domain = config['count_per_domain'])
    spider.do_verbs = config['do_verbs']
    
    await spider.start(config['start_url'])
    try:
        while True:
            if spider.is_active:
                await spider.step()
                time.sleep(spider.sleep_time)
                # if spider.step_number > 5:
                #     break
            # else:
                # time.sleep(spider.sleep_time)
            if killer.kill_now:
                break
    except KeyboardInterrupt as ex:
        print('goodbye!')


if __name__ == '__main__':

    now = datetime.now()
    date_time = now.strftime("%Y-%m-%d_%H-%M-%S")
    # log_file_name = f"db_{date_time}.log"
    log_file_name = f"db.log"
    
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
                        handlers=[
                            logging.FileHandler(log_file_name),
                            logging.StreamHandler(sys.stdout)
                        ],
                        # filemode='a',
                        encoding='utf-8',
                        level=logging.DEBUG,
                        datefmt='%Y-%m-%d %H:%M:%S')
    

    asyncio.run(main())