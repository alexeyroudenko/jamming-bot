FROM python:3.6-stretch

#This command will create the working directory for our Python Flask application Docker image
WORKDIR /app

#This command will copy the dependancies and libaries in the requirements.txt to the working directory
# COPY requirements.txt /code

#This command will install the dependencies in the requirements.txt to the Docker image
#RUN pip install -r requirements.txt --no-cache-dir

RUN pip install redis
RUN pip install eventlet

# RUN pip install python-socketio=="4.6.0"
# RUN pip install python-engineio=="3.13.2"
# RUN pip install Flask-SocketIO=="4.3.1"

RUN pip install python-socketio=="5.11.0"
RUN pip install python-engineio=="4.10.1"
RUN pip install Flask-SocketIO=="5.4.1"


RUN pip install Flask-Cors
RUN pip install Flask
RUN pip install rq==1.2.0
RUN pip install rq-dashboard==0.5.1
RUN pip install gunicorn==19.9.0
RUN pip install click
RUN pip install sentry-sdk[flask]
RUN pip install requests

# RUN pip install -U spacy
# RUN python -m spacy download en_core_web_sm
# RUN python -m spacy download en_core_web_lg

# Make port 5000 available to the world outside this container
EXPOSE 5000
EXPOSE 9999

# Define environment variable
ENV NAME World

#This command will copy the files and source code required to run the application
# COPY app/flask/ /app

#This command will start the Python Flask application Docker container
# CMD python app.py

# ENTRYPOINT ["python", "app.py"]