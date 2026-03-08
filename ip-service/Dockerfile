FROM python:3.12-slim

WORKDIR /app

# DB-IP City Lite (free, monthly updates): https://db-ip.com/db/download/ip-to-city-lite
ARG DBIP_VERSION=2026-02
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc wget ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /app/data/db \
    && wget -q "https://download.db-ip.com/free/dbip-city-lite-${DBIP_VERSION}.mmdb.gz" -O /tmp/dbip.mmdb.gz \
    && gunzip -c /tmp/dbip.mmdb.gz > /app/data/db/dbip-city-lite.mmdb \
    && rm /tmp/dbip.mmdb.gz

COPY ./requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt \
    && rm -rf /root/.cache/pip

EXPOSE 80:8080

COPY . /app/