FROM python:3.12-slim

WORKDIR /app

# GeoLite2 City (free with MaxMind license key): https://dev.maxmind.com/geoip/geolite2-free-geolocation-data
ARG GEOLITE2_EDITION_ID=GeoLite2-City
ARG MAXMIND_LICENSE_KEY
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc wget ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /app/data/db \
    && if [ -z "$MAXMIND_LICENSE_KEY" ]; then echo "MAXMIND_LICENSE_KEY is required"; exit 1; fi \
    && wget -q "https://download.maxmind.com/app/geoip_download?edition_id=${GEOLITE2_EDITION_ID}&license_key=${MAXMIND_LICENSE_KEY}&suffix=tar.gz" -O /tmp/geolite2.tar.gz \
    && tar -xzf /tmp/geolite2.tar.gz --wildcards --no-anchored "GeoLite2-City.mmdb" -O > /app/data/db/GeoLite2-City.mmdb \
    && rm /tmp/geolite2.tar.gz

COPY ./requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt \
    && rm -rf /root/.cache/pip

EXPOSE 80:8080

COPY . /app/