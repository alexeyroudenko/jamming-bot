FROM python:3.11-slim

#This command will create the working directory for our Python Flask application Docker image
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt --no-cache-dir

# Make port 5000 available to the world outside this container
EXPOSE 5000
EXPOSE 9999

# Define environment variable
ENV NAME=World

#This command will copy the files and source code required to run the application
COPY flask/ /app

#This command will start the Python Flask application Docker container
# Use Gunicorn + eventlet for production (Flask-SocketIO compatible)
CMD ["gunicorn", "-k", "eventlet", "-w", "1", "-b", "0.0.0.0:5000", "--timeout", "120", "app:app"]