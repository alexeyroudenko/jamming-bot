from pythonosc import udp_client

class Simulator():
    """Simulator 
    """
    def __init__(self):
        # self.osc = udp_client.SimpleUDPClient("224.0.1.255", 7000)
        self.osc = udp_client.SimpleUDPClient("192.168.31.18", 7002)
        self.step = 0
        self.init_data()
        self.socketio = None
        self.text = ""
        self.depency = ""
        self.read_source()
        self.read_semantic()              
        
    def init_data(self):
        self.step = 0
     
    def read_semantic(self):
        filename = "semantic/semantic.txt"
        with open(filename) as file:
            depency = [line.rstrip() for line in file]
            self.depency = depency
                  
    def read_source(self):
        source = "semantic/source.txt"
        with open(source, "r", encoding="utf-8") as file:
            content = file.read()
            self.text = content
        
    def get_step(self):        
        # data_ar = self.text.split(" ")    
        # url = data_ar[(self.step+1) % len(data_ar)]        
        # src = data_ar[self.step % len(data_ar)]
                
        link = self.depency[self.step].split(">")
        src = link[0]
        url = link[1]
        self.step = self.step + 1
        
        node = {}
        node['id'] = self.step
        node['step'] = self.step
        node['size'] = 5
        node['src'] = src
        node['url'] = url
        return node

    def simulate(self):  
        if self.step < len(self.depency):
            self.do_step()
        elif self.step > 1000:
            self.restart()
        else:
            self.restart()
            # self.restart()
            
    def do_step(self):
        n = self.get_step()
        values = n.values()
        self.osc.send_message("/step", values)
        self.socketio.emit('node', n)
        
    def do_skip(self):
        self.step = self.step + 1
        values = [self.step]
        self.osc.send_message("/skip", values)
        self.socketio.emit('skip', values)
        
    def restart(self):
        self.step = 0
        self.socketio.emit('restart')
        self.socketio.emit('clear')