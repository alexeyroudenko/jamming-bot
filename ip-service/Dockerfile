FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt \
    && rm -rf /root/.cache/pip

COPY . /app/

# DB-IP City Lite (CC BY 4.0) — no license key. Attribution: https://db-ip.com
# Downloaded after COPY so an empty host data/ dir cannot wipe the DB.
ARG DBIP_MMDB_URL=https://cdn.jsdelivr.net/npm/dbip-city-lite/dbip-city-lite.mmdb.gz
RUN mkdir -p /app/data/db \
    && curl -fsSL "${DBIP_MMDB_URL}" | gunzip -c > /app/data/db/dbip-city-lite.mmdb \
    && test -s /app/data/db/dbip-city-lite.mmdb

EXPOSE 8004
