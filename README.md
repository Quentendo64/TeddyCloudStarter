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

3. Edit the .env file with your actual domain, email, and optional IP filtering:
   ```bash
   DOMAIN_NAME=yourdomain.com
   LETSENCRYPT_MAIL=your-email@example.com

   # Optional: Restrict access to specific IPs. Leave empty to disable 
   ALLOWED_IPS_WEB="192.168.1.1 192.168.1.2 192.168.1.3"  # Space-separated list of allowed IPs for the web interface
   ALLOWED_IPS_BACKEND="10.0.0.1 10.0.0.2"               # Space-separated list of allowed IPs for the backend
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
├── .env                 # Environment variables (you'll create this)
├── .env.example         # Example environment file
├── docker-compose.yml   # Docker Compose configuration
├── Init.sh              # Initialization script for SSL setup
├── nginx.conf           # Nginx configuration (Init.sh create this)
├── nginx.conf.template  # Nginx configuration Template
├── htpasswd             # User authentication file (you'll create this)
└── data/                # Created on first run, contains persistent data (Init.sh create this)
    └── certbot/         # SSL certificates
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
- **Port 443**: Required for HTTPS connections from your Tonieboxes / To the administrative Panel.

### DNS Configuration
Ensure your domain name is properly configured with an A record pointing to your server's public IP address. Allow 24-48 hours for DNS propagation if you've just set this up. Be aware of the DNS cache.

## TeddyCloud Access & Usage

### Accessing TeddyCloud
Once your server is up and running:
1. Access the TeddyCloud admin panel at: `https://yourdomain.com`
2. Log in with the credentials you created in your htpasswd file
3. The admin interface allows you to:
   - Manage Tonieboxes connected to your server
   - Upload and organize content
   - Assign content to Tonies
   - View logs and connection status

### Configuring Your Toniebox
To connect your Toniebox to your TeddyCloud server:
1. Follow the Guides at: `https://yourdomain.com/web/tonieboxes/boxsetup`

## Security Best Practices

To ensure your TeddyCloud setup is secure, follow these recommendations:

1. **Use Strong Passwords**: When creating the `htpasswd` file, use a strong and unique password for authentication.
2. **Restrict Access**: Limit access to your TeddyCloud server by using the `ALLOWED_IPS_WEB` and `ALLOWED_IPS_BACKEND` environment variables to specify trusted IPs. For example:
   ```bash
   ALLOWED_IPS_WEB="192.168.1.1 192.168.1.2"
   ALLOWED_IPS_BACKEND="10.0.0.1 10.0.0.2"
   ```
3. **Keep Software Updated**: Regularly update Docker, Docker Compose, and TeddyCloud to the latest versions to patch vulnerabilities.
4. **Enable Automatic Certificate Renewal**: Certbot automatically renews certificates, but ensure the renewal process is working by testing it periodically.
5. **Monitor Logs**: Regularly review logs for suspicious activity using:
   ```bash
   docker compose logs -f
   ```
6. **Backup Regularly**: Create backups of your data and certificates to recover quickly in case of an issue.

## Maintenance

### Updating TeddyCloud
To update your TeddyCloud installation to the latest version:

```bash
# Pull the latest images
docker compose pull

# Restart with the new images
docker compose up -d
```

### Backup and Restore
Regular backups are recommended for your TeddyCloud data:

```bash
# Create a backup of all volumes
docker run --rm -v teddycloudstarter_certs:/certs -v teddycloudstarter_config:/config -v teddycloudstarter_content:/content -v teddycloudstarter_library:/library -v teddycloudstarter_custom_img:/custom_img -v teddycloudstarter_firmware:/firmware -v teddycloudstarter_cache:/cache -v "$(pwd)/backup:/backup" alpine tar czf /backup/teddycloud-backup-$(date +%Y%m%d).tar.gz /certs /config /content /library /custom_img /firmware /cache

# Restore from backup (replace with your backup filename) !! DELETES ALL EXISTING FILES
docker run --rm -v teddycloudstarter_certs:/certs -v teddycloudstarter_config:/config -v teddycloudstarter_content:/content -v teddycloudstarter_library:/library -v teddycloudstarter_custom_img:/custom_img -v teddycloudstarter_firmware:/firmware -v teddycloudstarter_cache:/cache -v "$(pwd)/backup:/backup" alpine sh -c "rm -rf /certs/* /config/* /content/* /library/* /custom_img/* /firmware/* /cache/* && tar xzf /backup/teddycloud-backup-XXXXXXX.tar.gz -C /"

# Create a backup of teddycloud certificates
docker run --rm -v teddycloudstarter_certs:/certs -v "$(pwd)/backup:/backup" alpine tar czf /backup/teddycloud-certs-backup-$(date +%Y%m%d).tar.gz /certs

# Create a backup of teddycloud certificates
docker run --rm -v teddycloudstarter_config:/config -v "$(pwd)/backup:/backup" alpine tar czf /backup/teddycloud-config-backup-$(date +%Y%m%d).tar.gz /config

# Show content of a backup file (replace with your backup filename)
tar -tf backup/teddycloud-backup-XXXXXXX.tar.gz
```

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

### Troubleshooting Commands Cheat Sheet

#### Container Management
```bash
# View running containers
docker ps

# View all containers (including stopped)
docker ps -a

# Start/stop specific container
docker start teddycloud
docker stop teddycloud

# Restart specific container
docker restart teddycloud
```

#### Container Shell Access
```bash
# Access the container [teddycloud, nginx] shells
docker exec -it teddycloud /bin/bash
docker exec -it nginx /bin/bash

# Access the container [certbot] shells
docker exec -it certbot /bin/sh

# Run specific command in container
docker exec container_name command
```

#### Docker Compose Commands
```bash
# View logs of all services
docker compose logs

# View logs of specific service like teddycloud
docker compose logs teddycloud

# View logs of specific service like teddycloud and follow (live-view)
docker compose logs -f teddycloud

# View logs of specific service like teddycloud and follow (live-view) + last 100 lines
docker compose logs -f -n 100 teddycloud

# Restart all services
docker compose restart

# Rebuild and restart services
docker compose up -d --build

# Stop all services
docker compose down
```

#### TeddyCloud Specifics
```bash
# List client certificate folder
docker exec teddycloud ls /teddycloud/certs/client

# List server certificate folder
docker exec teddycloud ls /teddycloud/certs/server

```

## Community & Support

- **GitHub Issues**: Report bugs or request features on the for TeddyCloud here: [TeddyCloud GitHub repository](https://github.com/toniebox-reverse-engineering/teddycloud)
- **Wiki**: Comprehensive documentation at the official [Toniebox Wiki](https://tonies-wiki.revvox.de/)

## License

This project is licensed under GNU GPL v2. See the LICENSE file for details.