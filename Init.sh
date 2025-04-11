#!/bin/bash
set -e

# Load environment variables
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Validate environment variables
if [ -z "$DOMAIN_NAME" ]; then
  echo "ERROR: DOMAIN_NAME environment variable is not set. Please set it in your .env file."
  exit 1
fi

if [ -z "$LETSENCRYPT_MAIL" ]; then
  echo "ERROR: LETSENCRYPT_MAIL environment variable is not set. Please set it in your .env file."
  exit 1
fi

echo "Setting up certificates for $DOMAIN_NAME with email $LETSENCRYPT_MAIL"

# Create necessary directories
mkdir -p ./data/certbot/conf/live/$DOMAIN_NAME
mkdir -p ./data/certbot/www

echo "Generating nginx configuration..."
cp nginx.conf.template nginx.conf
sed -i "s/example.com/$DOMAIN_NAME/g" nginx.conf

echo "Creating temporary self-signed certificate..."
# Create temporary self-signed certificate
docker compose run --rm --entrypoint "/bin/sh" certbot -c "mkdir -p /etc/letsencrypt/live/$DOMAIN_NAME && openssl req -x509 -nodes -newkey rsa:4096 -days 1 -keyout /etc/letsencrypt/live/$DOMAIN_NAME/privkey.pem -out /etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem -subj '/CN=$DOMAIN_NAME'"

# Start nginx with self-signed cert
echo "Starting Services..."
docker compose up -d

echo "Removing temporary self-signed certificate..."
# Remove temporary self-signed certificate
docker compose exec -it certbot rm -rf /etc/letsencrypt/live/$DOMAIN_NAME

echo "Requesting Let's Encrypt certificate for $DOMAIN_NAME..."
# Request proper certificates
docker compose exec -it certbot certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email $LETSENCRYPT_MAIL \
  --domain $DOMAIN_NAME \
  --rsa-key-size 4096 \
  --agree-tos \
  --verbose \
  --non-interactive \

echo "Restarting Nginx with new certificates..."
docker compose restart nginx certbot

echo "Certificate setup complete! You can now start the services with 'docker compose up -d'"