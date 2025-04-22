#!/usr/bin/env python3
"""
Configurations for TeddyCloudStarter.
This module contains all templates used in the application.
"""

DOCKER_COMPOSE = """
name: teddycloudstarter
services:
  {%- if mode == "nginx" %}
  # Edge Nginx - Handles SNI routing and SSL termination
  nginx-edge:
    container_name: teddycloud-edge
    hostname: {{ domain }}
    image: nginx:stable-alpine
    command: "/bin/sh -c 'while :; do sleep 6h & wait $${!}; nginx -s reload; done & nginx -g \\\"daemon off;\\\"'"
    volumes:
      - ./configurations/nginx-edge.conf:/etc/nginx/nginx.conf:ro
      {%- if https_mode == "letsencrypt" %}
      - certbot_conf:/etc/letsencrypt:ro
      - certbot_www:/var/www/certbot:ro
      {%- else %}
      - ./server_certs:/etc/nginx/certs:ro
      {%- endif %}
      - nginx_logs:/var/log/nginx
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
    networks:
      - frontend
      - backend

  {%- if security_type == "client_cert" %}
  # Backend Nginx - Handles client certificate authentication
  nginx-auth:
    container_name: teddycloud-auth
    hostname: teddycloud-auth
    image: nginx:stable-alpine
    command: "/bin/sh -c 'while :; do sleep 6h & wait $${!}; nginx -s reload; done & nginx -g \\\"daemon off;\\\"'"
    volumes:
      - certs:/teddycloud/certs:ro
      - ./configurations/nginx-auth.conf:/etc/nginx/nginx.conf:ro
      - ./client_certs:/etc/nginx/client_certs:ro
      - nginx_logs:/var/log/nginx_auth
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "nginx", "-t"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    networks:
      - backend
  {%- endif %}
  {%- endif %}

  # TeddyCloud - Main application server
  teddycloud:
    container_name: teddycloud{% if mode == "nginx" %}-app{% endif %}
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
      # These ports can be adjusted based on your configuration
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
    networks:
      - backend
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
    networks:
      - frontend
  {%- endif %}

# Persistent storage volumes
volumes:
  certs:      # SSL/TLS certificates
  config:     # TeddyCloud configuration
  content:    # Toniebox content storage
  library:    # Toniebox library storage
  custom_img: # Custom images for content
  firmware:   # Toniebox firmware storage
  cache:      # Toniebox cache storage
  {%- if mode == "nginx" %}
  nginx_logs: # Consolidated nginx logs
  {%- if https_mode == "letsencrypt" %}
  certbot_conf: # Certbot certificates and configuration
  certbot_www:  # Certbot ACME challenge files
  {%- endif %}

# Network configuration
networks:
  frontend:
    name: teddycloud-frontend
  backend:
    name: teddycloud-backend
  {%- endif %}
"""

NGINX_EDGE = """# TeddyCloud Edge Nginx Configuration
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
    
    # Define upstream servers
    upstream teddycloud_admin {
        server teddycloud-app:80;
    }
    
    upstream teddycloud_box {
        server teddycloud-app:443;
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
    
    upstream teddycloud_admin {
        server teddycloud-app:80;
    }
    
    upstream teddycloud_box {
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

NGINX_AUTH = """# TeddyCloud Auth Nginx Configuration
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    # This server only handles HTTPS traffic
    server {
        listen 443 ssl;
        
        ssl_certificate /etc/nginx/client_certs/server/server.crt;
        ssl_certificate_key /etc/nginx/client_certs/server/server.key;
        ssl_client_certificate /etc/nginx/client_certs/ca/ca.crt;
        ssl_verify_client on;
        
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_prefer_server_ciphers off;
        
        {%- if allowed_ips %}
        # IP restriction
        {% for ip in allowed_ips %}
        allow {{ ip }};
        {% endfor %}
        deny all;
        {%- endif %}
        
        # Forward all requests to TeddyCloud SSL backend
        location / {
            proxy_pass https://teddycloud-app:443;
            proxy_set_header Host $host;
            proxy_ssl_verify off;
        }
    }
}
"""

# Dictionary to store all templates for easy access
TEMPLATES = {
    "docker-compose": DOCKER_COMPOSE,
    "nginx-edge": NGINX_EDGE,
    "nginx-auth": NGINX_AUTH
}