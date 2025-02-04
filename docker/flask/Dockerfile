
#The Flask application container will use python:3.10-alpine as the base image
FROM python:3.8-slim


#This command will create the working directory for our Python Flask application Docker image
WORKDIR /app

#This command will copy the dependancies and libaries in the requirements.txt to the working directory
# COPY requirements.txt /code

#This command will install the dependencies in the requirements.txt to the Docker image
#RUN pip install -r requirements.txt --no-cache-dir
RUN pip install Flask
RUN pip install redis
# RUN pip install gevent
RUN pip install eventlet
# RUN pip install gevent-websocket 
RUN pip install flask-socketio

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variable
ENV NAME World

#This command will copy the files and source code required to run the application
# COPY app/flask/ /app

#This command will start the Python Flask application Docker container
# CMD python app.py

ENTRYPOINT ["python", "app.py"]