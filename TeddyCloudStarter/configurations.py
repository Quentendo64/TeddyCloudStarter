#!/usr/bin/env python3
"""
Configurations for TeddyCloudStarter.
This module contains all templates used in the application.
"""

DOCKER_COMPOSE = """
################################################################################
#                               WARNING                                        #
#       DO NOT MODIFY THIS FILE MANUALLY. IT IS MANAGED BY TEDDYCLOUDSTARTER.  #
#       ANY MANUAL CHANGES WILL BE OVERWRITTEN ON NEXT GENERATION.             #
################################################################################

name: teddycloudstarter
services:
  {%- if mode == "nginx" %}
  nginx-edge:
    container_name: nginx-edge
    tty: true
    hostname: {{ domain }}
    environment:
      - NGINX_DEBUG=all
      - SSL_TRACE=4
    image: nginx:stable-alpine
    command: "/bin/sh -c 'while :; do sleep 6h & wait $${!}; nginx -s reload; done & nginx -g \\\"daemon off;\\\"'"
    volumes:
      - ./configurations/nginx-edge.conf:/etc/nginx/nginx.conf:ro
      {%- if https_mode == "letsencrypt" %}
      - certbot_conf:/etc/letsencrypt:ro
      - certbot_www:/var/www/certbot:ro
      {%- endif %}
    ports:
      - 80:80
      - 443:443
    restart: unless-stopped
    depends_on:
      - teddycloud
      - nginx-auth
    healthcheck:
      test: ["CMD", "nginx", "-t"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  nginx-auth:
    container_name: nginx-auth
    tty: true
    hostname: nginx-auth
    environment:
      - NGINX_DEBUG=all
      - SSL_TRACE=4
    image: nginx:stable-alpine
    command: "/bin/sh -c 'while :; do sleep 6h & wait $${!}; nginx -s reload; done & nginx -g \\\"daemon off;\\\"'"
    volumes:
      - ./configurations/nginx-auth.conf:/etc/nginx/nginx.conf:ro
      {% if https_mode == "custom" %}
      - {{ cert_path }}
      {%- endif %}
      {% if https_mode == "self_signed" %}
      - {{ cert_path }}
      {%- endif %}
      {% if https_mode == "user_provided" %}
      - {{ cert_path }}
      {%- endif %}
      {%- if security_type == "client_cert" %}
      - ./client_certs/ca:/etc/nginx/ca:ro
      {% if crl_file %}
      - ./client_certs/crl:/etc/nginx/crl:ro
      {%- endif %}
      {%- endif %}
      {%- if security_type == "basic_auth" %}
      - ./security:/etc/nginx/security:ro
      {%- endif %}
      {%- if https_mode == "letsencrypt" %}
      - certbot_conf:/etc/letsencrypt:ro
      - certbot_www:/var/www/certbot:ro
      {%- endif %}
      {% if nginx_type == "extended" %}
      - certs:/teddycloud/certs:ro
      {%- endif %}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "nginx", "-t"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
  {%- endif %}

  teddycloud:
    container_name: teddycloud-app
    tty: true
    hostname: teddycloud
    image: ghcr.io/toniebox-reverse-engineering/teddycloud:{{ teddycloud_image_tag|default('latest') }}
    volumes:
      - certs:/teddycloud/certs
      - config:/teddycloud/config
      - content:/teddycloud/data/content
      - library:/teddycloud/data/library
      - custom_img:/teddycloud/data/www/custom_img
      - custom_img:/teddycloud/data/library/custom_img
      - firmware:/teddycloud/data/firmware
      - cache:/teddycloud/data/cache
    {%- if mode == "direct" %}
    ports:
      {%- if admin_http %}
      - {{ admin_http }}:80
      {%- endif %}
      {%- if admin_https %}
      - {{ admin_https }}:8443
      {%- endif %}
      - {{ teddycloud }}:443
    {%- endif %}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s
    {%- if mode == "nginx" %}
    {%- endif %}

  {%- if mode == "nginx" and https_mode == "letsencrypt" %}
  certbot:
    container_name: teddycloud-certbot
    image: certbot/certbot:latest
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"
    volumes:
      - certbot_conf:/etc/letsencrypt
      - certbot_www:/var/www/certbot
      - certbot_logs:/var/log/letsencrypt
    restart: unless-stopped
    depends_on:
      - nginx-edge

  {%- endif %}

volumes:
  certs:
  config:
  content:
  library:
  custom_img:
  firmware:
  cache:
  {%- if mode == "nginx" %}
  {%- if https_mode == "letsencrypt" %}
  certbot_conf:
  certbot_www:
  certbot_logs:
  {%- endif %}
  {%- endif %}
"""

NGINX_EDGE = """################################################################################
#                               WARNING                                        #
#       DO NOT MODIFY THIS FILE MANUALLY. IT IS MANAGED BY TEDDYCLOUDSTARTER.  #
#       ANY MANUAL CHANGES WILL BE OVERWRITTEN ON NEXT GENERATION.             #
################################################################################

user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format teddystarter_format 'Log: $remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent"';
    access_log /var/log/nginx/access.log teddystarter_format;

    upstream teddycloud_http {
        server teddycloud-app:80;
    }

    server {
        listen 80;
        server_name {{ domain }};

        location / {
            return 301 https://$host$request_uri;
        }

        {%- if https_mode == "letsencrypt" %}
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }
        {%- endif %}
    }
}

stream {
    log_format stream_detailed 'StreamLog: $remote_addr [$time_local] '
                       '$protocol $status $bytes_sent $bytes_received '
                       '$session_time $ssl_protocol $ssl_cipher '
                       'BACKEND=$upstream '
                       'VERIFY=$ssl_client_verify '
                       'SESSION_ID=$ssl_session_id '
                       'SESSION_REUSE=$ssl_session_reused '

    log_format stream_basic 'StreamLog: $remote_addr [$time_local] '
                       '$protocol $status $bytes_sent $bytes_received '
                       '$session_time';

    map $ssl_preread_server_name $upstream {
        {{ domain }} teddycloud_admin;
        default teddycloud_box;
    }

    upstream teddycloud_admin {
        server nginx-auth:443;
    }
    {% if nginx_type == "extended" %}
    upstream teddycloud_box {
        server nginx-auth:9443;
    }
    {% else %}
    upstream teddycloud_box {
        server teddycloud-app:443;
    }
    {% endif %}

    server {
        {%- if allowed_ips %}
        {% for ip in allowed_ips %}
        allow {{ ip }};
        {% endfor %}
        deny all;
        {%- endif %}
        listen 443;
        ssl_preread on;
        ssl_certificate_cache off;
        ssl_session_cache off;
        proxy_ssl_conf_command Options UnsafeLegacyRenegotiation;
        proxy_pass $upstream;
    }
}
"""

NGINX_AUTH = """################################################################################
#                               WARNING                                        #
#       DO NOT MODIFY THIS FILE MANUALLY. IT IS MANAGED BY TEDDYCLOUDSTARTER.  #
#       ANY MANUAL CHANGES WILL BE OVERWRITTEN ON NEXT GENERATION.             #
################################################################################

user nginx;
worker_processes auto;

error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    sendfile        on;
    tcp_nopush      on;
    keepalive_timeout  65;
    log_format teddystarter_format 'Log: $remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent"';
    access_log /var/log/nginx/access.log teddystarter_format;
    ssl_session_tickets       off;
    ssl_session_cache         none;
    proxy_request_buffering   off;
    proxy_buffering           off;

    {% if security_type == "basic_auth" and auth_bypass_ips %}
    geo $auth_bypass {
        default 0;
        {% for ip in auth_bypass_ips %}
        {{ ip }} 1;
        {% endfor %}
    }

    map $auth_bypass $auth_basic_realm {
        0 "TeddyCloud Admin Area";
        1 "off";
    }
    {% endif %}

    server {
        listen 443 ssl;
        listen [::]:4443 ssl;
        server_tokens off;
        {%if https_mode == "letsencrypt" %}
        ssl_certificate /etc/letsencrypt/live/{{ domain }}/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/{{ domain }}/privkey.pem;
        {% else %}
        ssl_certificate /etc/nginx/certificates/server.crt;
        ssl_certificate_key /etc/nginx/certificates/server.key;
        {%- endif %}
        {% if security_type == "client_cert" %}
        ssl_client_certificate /etc/nginx/ca/ca.crt;
        {% if crl_file %}
        ssl_crl /etc/nginx/crl/ca.crl;
        {%- endif %}
        ssl_verify_client on;
        {%- endif %}
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_prefer_server_ciphers on;
        ssl_ciphers "ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256";
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 1d;
        ssl_session_tickets off;

        location / {
            client_max_body_size 4096M;
            {% if security_type == "basic_auth" %}
            {% if auth_bypass_ips %}
            auth_basic $auth_basic_realm;
            auth_basic_user_file /etc/nginx/security/.htpasswd;
            {% else %}
            auth_basic "TeddyCloud Admin Area";
            auth_basic_user_file /etc/nginx/security/.htpasswd;
            {% endif %}
            {% endif %}
            add_header X-Frame-Options "SAMEORIGIN" always;
            add_header X-Content-Type-Options "nosniff" always;
            add_header X-XSS-Protection "1; mode=block" always;
            add_header Referrer-Policy "no-referrer-when-downgrade" always;
            proxy_request_buffering off;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Host $server_name;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_max_temp_file_size 4096M;
            proxy_connect_timeout  60s;
            proxy_read_timeout  10800s;
            proxy_send_timeout  10800s;
            send_timeout  10800s;
            proxy_buffers 8 16k;
            proxy_buffer_size 32k;
            proxy_busy_buffers_size 32k;
            proxy_pass http://teddycloud-app:80;
        }
    }
}
{% if nginx_type == "extended" %}
stream {
    log_format stream_detailed 'StreamLog: $remote_addr [$time_local] '
                       '$protocol $status $bytes_sent $bytes_received '
                       '$session_time $ssl_protocol $ssl_cipher '
                       'FP=$ssl_client_fingerprint '
                       'MAC=$mac_address '
                       'REJ=$stream_reject '
                       'BACKEND=$backend '
                       'VERIFY=$ssl_client_verify '
                       'SESSION_ID=$ssl_session_id '
                       'SESSION_REUSE=$ssl_session_reused '                       
                       'CLIENT_STATUS=$client_status '
                       'CLIENT_DN=$ssl_client_s_dn '
                       'CLIENT_SN=$ssl_client_serial '
                       'CLIENT_CERT=$ssl_client_raw_cert ';
    log_format stream_basic 'StreamLog: $remote_addr [$time_local] '
                       '$protocol $status $bytes_sent $bytes_received '
                       '$session_time';
    access_log /var/log/nginx/stream_access.log stream_detailed;
    error_log /var/log/nginx/stream_error.log debug;

    map $ssl_client_fingerprint $stream_reject {
        default 1;
        {% for box in boxes %}{{ box[0] }} 0;
        {% endfor %}
    }
    map $ssl_client_fingerprint $mac_address {
        default "000000000000";
        {% for box in boxes %}{{ box[0] }} {{ box[1] }};
        {% endfor %}
    }

    map $ssl_client_fingerprint $client_status {
        default "unknown_client";
        {% for box in boxes %}{{ box[0] }} "client_authorized";
        {% endfor %}
    }

    upstream authorized_backend {
        server teddycloud-app:443;
    }

    upstream rejected_backend {
        server 127.0.0.1:10;
    }

    map $stream_reject $backend {
        0 authorized_backend;
        1 rejected_backend;
    }

    server {
        listen 9443 ssl;
        listen [::]:9443 ssl;
        ssl_certificate /teddycloud/certs/server/teddy-cert.nginx.pem;
        ssl_certificate_key /teddycloud/certs/server/teddy-key.nginx.pem;
        ssl_client_certificate /teddycloud/certs/client/ca_chain.pem;
        ssl_ciphers HIGH:!aNULL:!MD5@SECLEVEL=0;
        ssl_verify_client optional_no_ca;        
        ssl_certificate_cache off;
        ssl_session_cache off;
        ssl_session_tickets off;
        proxy_connect_timeout  60s;
        proxy_timeout 10800s;
        access_log /var/log/nginx/stream_access.log stream_detailed;
        error_log /var/log/nginx/stream_error.log debug;
        proxy_pass $backend;
        proxy_socket_keepalive on;
        proxy_ssl on;
        proxy_ssl_certificate /teddycloud/certs/client/$mac_address/client.pem;
        proxy_ssl_certificate_key /teddycloud/certs/client/$mac_address/private.pem;
        proxy_ssl_verify off;
        proxy_ssl_conf_command Options UnsafeLegacyRenegotiation;
        proxy_ssl_protocols TLSv1.2 TLSv1.3;
        proxy_ssl_ciphers HIGH:!aNULL:!MD5@SECLEVEL=0;
        proxy_ssl_session_reuse off;
    }
}
{% endif %}
"""

TEMPLATES = {
    "docker-compose": DOCKER_COMPOSE,
    "nginx-edge": NGINX_EDGE,
    "nginx-auth": NGINX_AUTH,
}
