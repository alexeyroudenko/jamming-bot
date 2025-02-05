

class Simulator():
    """Simulator 
    """
    def __init__(self):
        self.step = 0
        self.init_data()
        self.socketio = None
        filename = "semantic/semantic.txt"
        
        with open(filename) as file:
            lines = [line.rstrip() for line in file]
            self.lines = lines
        # print(self.lines)
        
    def init_data(self):
        self.step = 0
        
    def get_step(self):
        
        text = "Jamming bot is a fantasy about a post-apocalyptic future, when the core functions of the internet and assistant bots are defeated and only one self-replicating bot remains, aimlessly browsing the internet. It is a bot that has no goal, only a path. Currently, spiders, crawlers and bots serve a service purpose. They act as search engines, collect information, automate the infrastructure of the internet. Jamming bot is a fantasy about a post-apocalyptic future, when the core functions of the internet and assistant bots are defeated and only one self-replicating bot remains, aimlessly browsing the internet, perhaps studying the general mood of humanity in the scraps of meaning on the pages of the internet. It is a bot that has no goal, only a path. Jamming Bot is a fascinating and slightly melancholic concept, where the last remaining bot represents the legacy of the digital age. Jamming Bot may symbolize the loneliness and permanence of technology that has transcended control and self-improvement. It is like an observer, dwelling among the fragments of information, trying to catch the residual traces of humanity in the scraps of text, in the ruined pages, perhaps even interpreting them as traces of a long-forgotten society. Its movement across the Internet can be seen as a reflection of human aspirations, searches, and experiences, as it accidentally intersects with different fragments of meaning that were once assembled into a single network."
        data_ar = text.split(" ")
    
        src = data_ar[self.step % len(data_ar)]
        
        link = self.lines[self.step].split(">")
        
        src = link[0]
        url = link[1]

        # url = data_ar[(self.step+1) % len(data_ar)]        
        
        self.step = self.step + 1
        node = {}
        node['id'] = self.step
        node['step'] = self.step
        node['size'] = 5
        node['src'] = src
        node['url'] = url
        
        return node

    def simulate(self):
        # print(f"Simulator::simulate {self.step}")
        # self.socketio.emit('simulate')
        
        if self.step < 255:
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