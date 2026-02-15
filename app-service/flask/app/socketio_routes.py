import time
import json


from config import getConfig, getRedis
cfg = getConfig()
redis = getRedis()



def socketio_handlers(socketio):
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
        
        
    # '''
    #     msg.channel 
    #     msg.data
    # '''
    @socketio.on('reset')
    def handle_reset():
        print('received reset')
        #redis.incr('hits')

    @socketio.on('connect')
    def handle_connect(message):
        #data = message['data']з
        print('connect message')

    @socketio.on('update')
    def handle_update(message):
        # print('update message: ' + str(msg))
        data = message['data']
        print('update message: ' + str(data))
        
    @socketio.on('message')
    def handle_message(message):
        print('received message: ' + message)    
        redis.incr('hits')
    
    # '''
    #     bot controlss
    #     
    # '''
    @socketio.on('start')
    def handle_start():
        print("handle start")
        redis.publish('ctrl', json.dumps("start"))
        
    @socketio.on('stop')
    def handle_stop():
        print("handle stop")
        redis.publish('ctrl', json.dumps("stop"))

    @socketio.on('restart')
    def handle_restart():
        socketio.emit('clear')     
        redis.publish('ctrl', json.dumps("restart"))

    @socketio.on('step')
    def handle_step():
        redis.publish('ctrl', json.dumps("step"))

    
    
    
    # redis.set('do_pass', float(1))

    # '''
    #     queue sockets
    #     
    # '''
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


    # @socketio.on('clean_tags')
    # def handle_clean_tags(value):
        # redis.set('clean_tags', float(value))


    # '''
    #     other
    #     
    # '''
    @socketio.event
    def my_ping():
        socketio.emit('my_pong')

    def event_trends_handler(msg):
        print(f"flask event_trends_handler {msg} ")
        socketio.emit('tags', msg)        
