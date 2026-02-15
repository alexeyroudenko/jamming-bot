from threading import Thread

from omegaconf import OmegaConf
from pythonosc.dispatcher import Dispatcher
from pythonosc import osc_server

def update_outputs_state(addr, args, value):
    outputs_state = args[0]
    outputs_state[addr[1:]] = value
    print(f"Feature state: {addr[1:]} - {value}")
    return outputs_state

class OSCServer:
    def __init__(
        self,
        osc_config: OmegaConf,
    ) -> None:
        self.osc_config = osc_config['osc_server']

        self.dispatcher = Dispatcher()
        # for feature_name in self.osc_config['feature_control']: 
        #    self.dispatcher.map(f"/{feature_name}", update_outputs_state, self.feature_states)

        self.server = osc_server.ThreadingOSCUDPServer((self.osc_config.adress, self.osc_config.port), self.dispatcher)

    def run_osc_reciver(self) -> None:
        print(f"serving osc ctrl {self.server.server_address}")
        self.thread = Thread(target=self.server.serve_forever)
        self.thread.start()

    def stop_osc_receiver(self) -> None:
        print("stop osc feature controler")
        self.server.server_close()