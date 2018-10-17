# Only for cloning repo
FROM ubuntu as intermediate

# install git
RUN apt-get update
RUN apt-get install -y git

# add credentials on build
RUN mkdir /root/.ssh/
COPY ./dockerkey /root/.ssh/id_rsa
COPY ./dockerkey.pub /root/.ssh/id_rsa.pub

# make sure your domain is accepted
RUN touch /root/.ssh/known_hosts
RUN ssh-keyscan bitbucket.org >> /root/.ssh/known_hosts
RUN git config --global core.sshCommand 'ssh -i /root/.ssh/id_rsa.pub'
RUN git clone --single-branch -b deploy git@bitbucket.org:strevg/parkpass-backend.git

FROM ubuntu:16.04
COPY --from=intermediate /parkpass-backend /srv/parkpass-backend

RUN \
  apt-get update && \
  apt-get install -y build-essential && \
  apt-get install -y software-properties-common && \
  apt-get install -y byobu curl git htop man unzip vim wget && \
  apt-get install -y nginx && \
  apt-get install -y supervisor && \
  rm -rf /var/lib/apt/lists/*

# Install Python2
RUN apt-get update && apt-get install -y python-dev && apt-get install -y python-pip

# Install Pillow ubuntu dependencies
RUN apt-get install -y libtiff5-dev libjpeg8-dev zlib1g-dev \
    libfreetype6-dev liblcms2-dev libgdal-dev libwebp-dev tcl8.6-dev tk8.6-dev python-tk

# Install OpenSSL for python
RUN apt-get install -y python-openssl

# Upgrade pip manager
RUN pip install --upgrade pip

# Setup all app requirements
RUN pip install -r /srv/parkpass-backend/requirements.txt

# Setup uwsgi log directory
RUN mkdir /var/log/uwsgi

WORKDIR /srv/parkpass-backend

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

# Debug django env
ARG DJANGO_DEBUG_FALSE=0
ENV DJANGO_DEBUG=$DJANGO_DEBUG_FALSE

# SMS-gateway env
ARG SMS_GATEWAY_ENABLE=1
ENV SMS_GATEWAY_ENABLE=$SMS_GATEWAY_ENABLE

# Root host for media files
ARG MEDIA_HOST="https://parkpass.ru/api"
ENV MEDIA_HOST=$MEDIA_HOST

# Set up volume for log-files
VOLUME /var/log

# Set up volume for static
VOLUME /app/files
