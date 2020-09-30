FROM python:3.6.9-buster

# update pip
RUN python3.6 -m pip install pip --upgrade
RUN python3.6 -m pip install wheel

# Install Pillow ubuntu dependencies
RUN apt-get install -y zlib1g-dev \
    libfreetype6-dev liblcms2-dev libwebp-dev tcl8.6-dev tk8.6-dev

# Install OpenSSL for python
# RUN apt-get install -y python-openssl

# Install parkpass project to /deploy
RUN mkdir -p /app
RUN mkdir -p /app/media/logs
RUN mkdir -p /app/media/reports

COPY /. /app

# Upgrade pip manager
RUN pip install --upgrade pip

# Setup all app requirements
RUN pip install -r /app/requirements.txt

# Setup uwsgi log directory
RUN mkdir /var/log/uwsgi

WORKDIR /app/

RUN cd lib && tar -xvf cmake-3.14.6-Linux-x86_64.tar.gz && cd cmake-3.14.6-Linux-x86_64 \
&& cp -r bin /usr/ && cp -r share /usr/ && cp -r doc /usr/share/ && cp -r man /usr/share/

RUN cd /app/lib/OpenXLSX && cmake . && make && cp output_restore_01.xlsm install/bin/output_restore_01.xlsm

# Config for socket upstream from nginx
ARG SOCKNAME_DEFAULT="app.sock"
ENV SOCKNAME=$SOCKNAME_DEFAULT
VOLUME /app/socket-dir

# Config for Database PostgreSQL
ARG POSTGRES_DB_NAME="main"
ARG POSTGRES_USER="parkpass"
ARG POSTGRES_PASSWORD="parkpass"
ARG POSTGRES_DATABASE_HOST="localhost"

ENV POSTGRES_DB_NAME=$POSTGRES_DB_NAME
ENV POSTGRES_USER=$POSTGRES_USER
ENV POSTGRES_PASSWORD=$POSTGRES_PASSWORD
ENV POSTGRES_DATABASE_HOST=$POSTGRES_DATABASE_HOST


ARG REDIS_HOST_DEFAULT="redis"
ARG REDIS_PORT_DEFAULT="6379"
ENV REDIS_HOST=$REDIS_HOST_DEFAULT
ENV REDIS_PORT=$REDIS_PORT_DEFAULT

# Debug django env
ARG DJANGO_DEBUG_FALSE=0
ENV DJANGO_DEBUG=$DJANGO_DEBUG_FALSE

ARG AUTOTASK_ENABLE_DEFAULT=0
ENV AUTOTASK_ENABLE=$AUTOTASK_ENABLE_DEFAULT

# SMS-gateway env
ARG SMS_GATEWAY_ENABLE=1
ENV SMS_GATEWAY_ENABLE=$SMS_GATEWAY_ENABLE

# Root host for media files
ARG MEDIA_HOST="https://parkpass.ru/api"
ENV MEDIA_HOST=$MEDIA_HOST

ARG ELASTICSEARCH_URL="http://185.158.155.26:9200"
ENV ELASTICSEARCH_URL=$ELASTICSEARCH_URL

ARG ELASTICSEARCH_USER="elastic"
ENV ELASTICSEARCH_USER=$ELASTICSEARCH_USER

ARG ELASTICSEARCH_PASSWORD="pass"
ENV ELASTICSEARCH_PASSWORD=$ELASTICSEARCH_PASSWORD

# Set up volume for log-files
VOLUME /var/log

# Set up volume for static
VOLUME /app/media