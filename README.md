# TeddyCloud Starter

A Docker-based setup for running your own TeddyCloud server for Tonieboxes.

## Overview

This repository contains the necessary files to quickly set up a TeddyCloud server using Docker. TeddyCloud allows your Tonieboxes to connect to your own server rather than the official Toniebox cloud service. Follow the official site for more information about TeddyCloud: https://tonies-wiki.revvox.de/docs/tools/teddycloud/

Shoutout to the great team that makes TeddyCloud happening:
https://github.com/toniebox-reverse-engineering

## Prerequisites

- Docker and Docker Compose installed
- A domain name pointed to your server
- Basic knowledge of terminal/command line
- Open ports 80 and 443 on your firewall/router
- Correctly configured DNS for your domain pointing to your server's IP address

## Quick Start

1. Clone this repository:
   ```bash
   git clone https://github.com/Quentendo64/TeddyCloudStarter.git
   cd TeddyCloudStarter
   ```

2. Copy the example environment file and configure it:
   ```bash
   cp .env.example .env
   ```

3. Edit the .env file with your actual domain and email:
   ```bash
   DOMAIN_NAME=yourdomain.com
   LETSENCRYPT_MAIL=your-email@example.com
   ```

4. Create an htpasswd file for authentication:
   ```bash
   htpasswd -c htpasswd yourusername
   ```

5. Run the initialization script to set up SSL certificates:
   ```bash
   chmod +x Init.sh
   ./Init.sh
   ```

6. Start the services:
   ```bash
   docker compose up -d
   ```

7. Your TeddyCloud server will be available at https://example.com

## Components

- **Nginx**: Handles HTTP/HTTPS requests, SSL termination, and proxies to TeddyCloud
- **TeddyCloud**: The main application that your Tonieboxes connect to
- **Certbot**: Automatically obtains and renews SSL certificates from Let's Encrypt

## Directory Structure

```
.
├── .env                 # Environment variables
├── .env.example         # Example environment file
├── docker-compose.yml   # Docker Compose configuration
├── Init.sh              # Initialization script for SSL setup
├── nginx.conf           # Nginx configuration
├── htpasswd             # User authentication file (you'll create this)
└── data/                # Created on first run, contains persistent data
    ├── certbot/         # SSL certificates
    └── ...
```

## Volumes

The setup creates several Docker volumes to persist data:

- `certs`: TLS certificates
- `config`: TeddyCloud configuration
- `content`: Content for Tonieboxes
- `library`: Content library
- `custom_img`: Custom images for custom Tonies
- `firmware`: Firmware backups
- `cache`: Image cache

## Network Configuration

### Required Ports
- **Port 80**: Required for initial Let's Encrypt certificate verification
- **Port 443**: Required for HTTPS connections from your Tonieboxes

### DNS Configuration
Ensure your domain name is properly configured with an A record pointing to your server's public IP address. Allow 24-48 hours for DNS propagation if you've just set this up. Be aware of the DNS cache.

## Troubleshooting

- **Certificate issues**: Run Init.sh again to reset certificates
- **Authentication issues**: Make sure your htpasswd file is properly created
- **Connection problems**: Check your domain DNS settings and firewall rules
- **Nginx fails to start**: Check if ports 80 and 443 are already in use by another service
- **Certificate renewal fails**: Ensure ports are open and DNS is configured correctly
- **Toniebox can't connect**: Verify your Toniebox is configured to use your TeddyCloud server
- **Content not appearing**: Check volume permissions and restart the container

### Common Issues

1. **Certificate Issues**
   - Error: "unknown domain_name variable"
     * Solution: Check if your .env file is properly loaded
     * Verify DOMAIN_NAME is set correctly
   - Error: "Unable to get certificates"
     * Solution: Ensure ports 80/443 are accessible
     * Check DNS settings are propagated

2. **Nginx Issues**
   - Error: "Address already in use"
     * Solution: Check if another service is using ports 80/443
     * Run `netstat -tulpen` to identify conflicting services
   - Error: "Failed to start nginx"
     * Solution: Check nginx.conf syntax
     * Verify all required files exist

3. **TeddyCloud Connection**
   - Error: "Connection refused"
     * Solution: Check if all containers are running
     * Verify firewall settings
   - Error: "Authentication failed"
     * Solution: Verify htpasswd file permissions
     * Recreate htpasswd file if needed

## License

This project is licensed under GNU GPL v2. See the LICENSE file for details.