FROM python:3.11-slim

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
RUN pip install rq==1.16.2
RUN pip install rq-dashboard==0.6.1
RUN pip install gunicorn==23.0.0
RUN pip install click
RUN pip install sentry-sdk[flask]>=2.35.0

RUN pip install requests
RUN pip install prometheus-flask-exporter==0.20.3
RUN pip install boto3

# Install modern spaCy and models compatible with Python 3.11
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install "spacy==3.8.2"
# Install spaCy v3 English models
RUN python -m spacy download en_core_web_sm
RUN python -m spacy download en_core_web_md

# Make port 5000 available to the world outside this container
EXPOSE 5000
EXPOSE 9999

# Define environment variable
ENV NAME World

#This command will copy the files and source code required to run the application
COPY flask/ /app

#This command will start the Python Flask application Docker container
CMD ["python", "app.py"]