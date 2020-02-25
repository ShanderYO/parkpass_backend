FROM ubuntu:16.04

# Install.
RUN \
  apt-get update && \
  apt-get install -y build-essential && \
  apt-get install -y software-properties-common && \
  apt-get install -y byobu curl git htop man unzip vim wget && \
  apt-get install -y nginx && \
  apt-get install -y supervisor && \
  rm -rf /var/lib/apt/lists/*

# Install Python3
RUN apt-get update && \
  apt-get install -y software-properties-common && \
  add-apt-repository ppa:jonathonf/python-3.6
RUN apt-get update
RUN apt-get install -y build-essential python3.6 python3.6-dev python3-pip python3.6-venv
RUN apt-get install -y git

# update pip
RUN python3.6 -m pip install pip --upgrade
RUN python3.6 -m pip install wheel

# Install Pillow ubuntu dependencies
RUN apt-get install -y libtiff5-dev libjpeg8-dev zlib1g-dev \
    libfreetype6-dev liblcms2-dev libgdal-dev libwebp-dev tcl8.6-dev tk8.6-dev python-tk

# Install OpenSSL for python
RUN apt-get install -y python-openssl

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

# Set up volume for log-files
VOLUME /var/log

# Set up volume for static
VOLUME /app/media