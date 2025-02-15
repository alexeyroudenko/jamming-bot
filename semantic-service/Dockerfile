FROM python:3.6-stretch

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt

RUN pip install --upgrade pip

RUN pip install -r /app/requirements.txt \
    && rm -rf /root/.cache/pip

RUN pip install -U spacy
RUN python -m spacy download en_core_web_sm
RUN python -m spacy download en_core_web_lg

EXPOSE 80:8080

COPY . /app/