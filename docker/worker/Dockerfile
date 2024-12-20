
FROM python:3.6-stretch

WORKDIR /app

RUN pip install redis
RUN pip install eventlet

RUN pip install python-socketio=="4.6.0"
RUN pip install python-engineio=="3.13.2"
RUN pip install Flask-SocketIO
RUN pip install Flask-Cors
RUN pip install Flask
RUN pip install rq==1.2.0
RUN pip install rq-dashboard==0.5.1
RUN pip install gunicorn==19.9.0
RUN pip install "click>=7,<8"
RUN pip install -U spacy
RUN python -m spacy download en_core_web_sm
RUN python -m spacy download en_core_web_lg
RUN pip install selenium
RUN pip install chromedriver
RUN pip install bs4
RUN pip install sentry-sdk[flask]