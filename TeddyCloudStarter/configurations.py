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
  # Edge Nginx - Handles SNI routing and SSL termination
  nginx-edge:
    container_name: nginx-edge
    tty: true
    hostname: {{ domain }}
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
    healthcheck:
      test: ["CMD", "nginx", "-t"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  
  # Backend Nginx - Handles authentication
  nginx-auth:
    container_name: nginx-auth
    tty: true
    hostname: nginx-auth
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
      - ./data/security:/etc/nginx/security:ro
      {%- endif %}
      {%- if https_mode == "letsencrypt" %}
      - certbot_conf:/etc/letsencrypt:ro
      - certbot_www:/var/www/certbot:ro
      {%- endif %}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "nginx", "-t"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
  {%- endif %}

  # TeddyCloud - Main application server
  teddycloud:
    container_name: teddycloud-app
    tty: true
    hostname: teddycloud
    image: ghcr.io/toniebox-reverse-engineering/teddycloud:latest
    volumes:
      - certs:/teddycloud/certs        
      - config:/teddycloud/config         
      - content:/teddycloud/data/content  
      - library:/teddycloud/data/library  
      - custom_img:/teddycloud/data/www/custom_img
      - custom_img:/teddycloud/data/library/custom_img  # WORKAROUND: allows uploads to custom_img // Used by TonieToolbox
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
  # Certbot - Automatic SSL certificate management
  certbot:
    container_name: teddycloud-certbot
    image: certbot/certbot:latest
    # Renews certificates every 12 hours if needed
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"
    volumes:
      - certbot_conf:/etc/letsencrypt
      - certbot_www:/var/www/certbot
    restart: unless-stopped
    depends_on:
      - nginx-edge

  {%- endif %}

# Persistent storage volumes
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
  certbot_conf: # Certbot certificates and configuration
  certbot_www:  # Certbot ACME challenge files
  {%- endif %}
  {%- endif %}
"""

NGINX_EDGE = """################################################################################
#                               WARNING                                        #
#       DO NOT MODIFY THIS FILE MANUALLY. IT IS MANAGED BY TEDDYCLOUDSTARTER.  #
#       ANY MANUAL CHANGES WILL BE OVERWRITTEN ON NEXT GENERATION.             #
################################################################################

# TeddyCloud Edge Nginx Configuration
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

# HTTP server for redirects and ACME challenges
http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    # Log configuration
    log_format teddystarter_format 'Log: $remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent"';            
    access_log /var/log/nginx/access.log teddystarter_format;

    
    # Define upstream servers for HTTP
    upstream teddycloud_http {
        server teddycloud-app:80;
    }
    
    # HTTP server
    server {
        listen 80;
        server_name {{ domain }};
        
        # Redirect all HTTP traffic to HTTPS
        location / {
            return 301 https://$host$request_uri;
        }
        
        {%- if https_mode == "letsencrypt" %}
        # Let's Encrypt challenge location
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }
        {%- endif %}
    }
}

# HTTPS server with SNI detection
stream {  
    # Define the map for SNI detection
    map $ssl_preread_server_name $upstream {
        {{ domain }} teddycloud_admin;
        default teddycloud_box;
    }
    
    # Define upstream servers for HTTPS
    upstream teddycloud_admin {
                server nginx-auth:443;
            }
    
    upstream teddycloud_box {
        # Teddycloud API endpoint for boxes
        server teddycloud-app:443;
    }
    
    # SSL forwarding server
    server {
        {%- if allowed_ips %}
        {% for ip in allowed_ips %}
        allow {{ ip }};
        {% endfor %}
        deny all;
        {%- endif %}        
        listen 443;        
        ssl_preread on;
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

# TeddyCloud Auth Nginx Configuration
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
    
    # Log configuration
    log_format teddystarter_format 'Log: $remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent"';            
    access_log /var/log/nginx/access.log teddystarter_format;
    
    # Set up geo map for IP-based authentication bypass when using basic auth
    {% if security_type == "basic_auth" and auth_bypass_ips %}
    geo $auth_bypass {
        default 0;
        {% for ip in auth_bypass_ips %}
        {{ ip }} 1;
        {% endfor %}
    }
    
    # Map variable to conditionally set auth requirements
    map $auth_bypass $auth_basic_realm {
        0 "TeddyCloud Admin Area";
        1 "off";
    }
    {% endif %}
    
    server {
        listen 443 ssl;
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
        ssl_prefer_server_ciphers off;
        ssl_ciphers "ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256";

        # Forward all requests to TeddyCloud
        location / {
            {% if security_type == "basic_auth" %}
            {% if auth_bypass_ips %}
            # Apply basic auth conditionally based on IP
            auth_basic $auth_basic_realm;
            auth_basic_user_file /etc/nginx/security/.htpasswd;
            {% else %}
            # Always require authentication
            auth_basic "TeddyCloud Admin Area";
            auth_basic_user_file /etc/nginx/security/.htpasswd;
            {% endif %}
            {% endif %}
            
            proxy_pass http://teddycloud-app:80;  
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
"""

TEMPLATES = {
    "docker-compose": DOCKER_COMPOSE,
    "nginx-edge": NGINX_EDGE,
    "nginx-auth": NGINX_AUTH
}