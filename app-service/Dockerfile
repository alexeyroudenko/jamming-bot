FROM python:3.11-slim

#This command will create the working directory for our Python Flask application Docker image
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt --no-cache-dir

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
ENV NAME=World

#This command will copy the files and source code required to run the application
COPY flask/ /app

#This command will start the Python Flask application Docker container
CMD ["python", "app.py"]