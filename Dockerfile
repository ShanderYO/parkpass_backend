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

# Install Python2
RUN apt-get update && apt-get install -y python-dev && apt-get install -y python-pip

# Install Pillow ubuntu dependencies
RUN apt-get install -y libtiff5-dev libjpeg8-dev zlib1g-dev \
    libfreetype6-dev liblcms2-dev libgdal-dev libwebp-dev tcl8.6-dev tk8.6-dev python-tk

# Install OpenSSL for python
RUN apt-get install -y python-openssl

# Install pebbyweb project to /deploy
RUN mkdir -p /parkpass_backend
COPY /. /parkpass_backend

# Upgrade pip manager
RUN pip install --upgrade pip

# Setup all app requirements
RUN pip install -r /parkpass_backend/requirements.txt

# stop supervisor service as we'll run it manually
RUN service supervisor stop
RUN mkdir /var/log/gunicorn

RUN echo "daemon off;" >> /etc/nginx/nginx.conf
RUN rm /etc/nginx/sites-enabled/default

WORKDIR /parkpass_backend/

# Add service.conf
ADD ./deploy/service.conf /parkpass_backend/
RUN ln -s /parkpass_backend/service.conf /etc/nginx/conf.d/

# Add supervisor
ADD ./deploy/supervisord.conf /parkpass_backend/

RUN ln -s /parkpass_backend/supervisord.conf /etc/supervisor/conf.d/

# Install Gunicorn and Supervisor
RUN apt-get install -y gunicorn

# Expose port(s)
EXPOSE 80

ARG POSTGRES_DB_NAME="main"
ARG POSTGRES_USER="parkpass"
ARG POSTGRES_PASSWORD="parkpass"
ARG POSTGRES_DATABASE_HOST="localhost"

ENV POSTGRES_DB_NAME=$POSTGRES_DB_NAME
ENV POSTGRES_USER=$POSTGRES_USER
ENV POSTGRES_PASSWORD=$POSTGRES_PASSWORD
ENV POSTGRES_DATABASE_HOST=$POSTGRES_DATABASE_HOST

ENV DJANGO_DEBUG_FALSE=False
ENV MEDIA_HOST="https://parkpass.ru/api"

VOLUME /var/logs
VOLUME /parkpass_backend/media

CMD ./run_service.sh