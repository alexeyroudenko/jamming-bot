

class Simulator():
    """Simulator 
    """
    def __init__(self):
        self.step = 0
        self.init_data()
        self.socketio = None
        
    def init_data(self):
        self.step = 0
        
    def get_step(self):
        
        text = "Jammingbot is a fantasy on the theme of a post-apocalyptic future, when the main functions of the Internet and assistant bots will be defeated and only one self-replicating bot will remain, aimlessly plowing the Internet. This is a bot that has no goal, but only a path. Currently, spiders, crawlers and bots have a service purpose. They act as search engines, collect information, automate Internet infrastructure. Jammingbot is a fantasy about a post-apocalyptic future, when the main functions of the Internet and assistant bots are defeated and only one self-replicating bot remains, aimlessly plowing the Internet, perhaps studying the general mood of humanity in the scraps of meaning on the pages of the Internet. This is a bot that has no goal, but only a path."
        data_ar = text.split(" ")
    
        src = data_ar[self.step % len(data_ar)]
        url = data_ar[(self.step+1) % len(data_ar)]
        
        self.step = self.step + 1
        node = {}
        node['id'] = self.step
        node['step'] = self.step
        node['size'] = 20
        node['src'] = src
        node['url'] = url
        
        return node

    def simulate(self):
        # print(f"Simulator::simulate {self.step}")
        # self.socketio.emit('simulate')
        
        if self.step < 36:
            self.do_step()
        else:
            self.restart()
            
    def do_step(self):
        n = self.get_step()
        self.socketio.emit('node', n)
        
        
    def node(self):
        n = self.get_step()
        self.socketio.emit('node', n)
        
    def restart(self):
        self.step = 0
        self.socketio.emit('restart')
        self.socketio.emit('clear')