import glob
import urllib
import pickle
# from urllib.parse import quote as url_quote
from urllib.parse import quote  
from flask import jsonify
from flask import request
from flask import Flask, render_template
from flask_cors import CORS, cross_origin
from flask_socketio import SocketIO, emit, disconnect

from rq_helpers import queue, get_all_jobs
import jobs
from flask import render_template, Blueprint, jsonify, request, current_app, redirect



app = Flask(__name__, 
    static_url_path='/data', 
    static_folder='data', 
    template_folder='templates'
)

app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading") 
cors = CORS(app)

# import pickle  
from redis import Redis
redis = Redis(host='redis', port=6379)
  
@app.route('/')
@cross_origin()
def index():
    return render_template('index.html')

@app.route('/help/')
def help():
    return render_template('help.html')

@app.route('/api/graph/')
@cross_origin()
def api_graph():
    response = jsonify({})
    return response



# @app.route('/nodex/')
# def nodex():
#     return render_template('nodex.html')

# @app.route('/tags')
# def tags():
#     try:
#         trends = pickle.loads(redis.get("trends"))
#     except:
#         trends = ["#baystars", "#FGO", "#malatya", "たかほ", "カズラドロップ", "バーニス", "バーニス", "バーニス", "増田大輝", "バーニス"]
#     # images = glob.glob("static/tags/$STORM/*")
#     return jsonify(trends)

# @app.route('/day/') 
# def day_action():
#     redis.incr('day')
#     count = int(redis.get('day'))
#     redis.publish("day", "count")
#     return "sent"

# @app.route('/tag/<tag>') 
# def show_tag_images(tag):
#     path = f"data/tags/{tag}/*"
#     print(f"show_tag_images {tag} {path}")
#     images = glob.glob(path)
    
#     #print(images)
#     rimages = []
#     for img in images:
#         rimages.append(img.replace("#","%23")) #quote
        
#     calc_images = glob.glob("data/spot/{tag}*")
#     for img in calc_images:
#         rimages.append(img.replace("#","%23")) #quote
    
#     out_item = {}
    
#     import os
#     if os.path.isfile(f"data/spot/{tag}_blr.png"):
#         rimages.append(f"data/spot/{tag}_src.jpg".replace("#","%23"))
#         rimages.append(f"data/spot/{tag}_pal.png".replace("#","%23"))
#         rimages.append(f"data/spot/{tag}_col.png".replace("#","%23"))
#         rimages.append(f"data/spot/{tag}_som.png".replace("#","%23"))
#         rimages.append(f"data/spot/{tag}_blr.png".replace("#","%23"))
        
#     return jsonify(rimages)



@app.route('/state/') 
def load_state():
    img_path = f"data/spot/2024-[0-9][0-9]-[0-9][0-9]-[0-9][0-9]_blr.png"
    img = [glob.glob(img_path)[0]]       
    return jsonify(img)


# @app.route('/state_info/') 
# def load_state_info():
#     txts_path = f"data/spot/2024-[0-9][0-9]-[0-9][0-9]-[0-9][0-9].txt"
#     txt = glob.glob(txts_path)[0]
#     file = open(txt, "r")
#     colors = file.read().split("\n")
#     return jsonify(colors)

# @app.route('/tag/<tag_action>/<tag>/') 
# def tag_action(tag_action, tag):
#     print(tag_action, tag)
#     socketio.emit('tag', [tag_action, tag])
#     return tag_action + " " + tag
    
# @app.route('/tag_ctrl/<tag_action>/<tag>/') 
# def tag_ctrl(tag_action, tag):
#     #print(tag_action, tag)
#     socketio.emit('tag', [tag_action, tag])
#     redis.publish(f"{tag_action}", tag)    
#     return tag
   
# @app.route('/app_ctrl/<word_action>/<word>/') 
# def app_ctrl(word_action, word):
#     #print(tag_action, tag)
#     print("word", word_action, word)
#     socketio.emit('word', [word_action, word])
#     redis.publish(f"{word_action}", word)    
#     return word

# @app.route('/spots')
# def spots():
#     import os
#     print(os.getcwd())
#     rimages = []
#     for img in glob.glob("data/spot/*blr.png"):
#         filename = img.replace("#","%23")
#         tag = str(img).split("/")[2]
#         tag = str(tag)[:-8]
#         tag = tag.encode().decode('unicode-escape')
#         rimages.append({"filename":filename, "tag":tag}) #quote
#     return jsonify(rimages)






#
# Called from container
#
@app.route('/bot/step/', methods=['GET', 'POST'])
def step():
    if request.method == 'POST':
        data = request.form
        url = data['current_url']
        text = data['text']
        print(f"store {url} {text[0:32]}") 
        
        # store data
        redis.set(url, text)
        
        # run job
        #
        # print(f"start {url} {text[0:32]}")

        # num_iterations = 15
        # num_iterations = int(num_iterations)
        # job = jobs.wait.delay(num_iterations)
        # response_object = {
        #     "status": "success",
        #     "data": {
        #         "job_id": job.get_id()
        #     }
        # }
        # status_code = 200
        # print(f"started job {job.get_id()}") 


    socketio.emit('step', [request.form])
    return "step"

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
 
@socketio.event
def my_ping():
    emit('my_pong')

# '''
#     msg.channel 
#     msg.data
# '''
def event_trends_handler(msg):
    print(f"flask event_trends_handler {msg} --------------------------- ")
    emit('tags', msg)
  
if __name__ == '__main__':
    print("start flask 1.1.0") 

    socketio.run(app, host='0.0.0.0', allow_unsafe_werkzeug=True, debug=True)