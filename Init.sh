#!/bin/bash
set -e

# Confirm overwriting nginx.conf
if [ -f nginx.conf ]; then
  echo "WARNING: The file 'nginx.conf' already exists and will be overwritten during runtime."
  echo "Any custom configurations in the existing file will be lost."
  read -p "Do you want to continue? (y/n): " confirm
  if [[ "$confirm" != "y" ]]; then
    echo "Operation aborted by the user."
    exit 1
  fi
fi

# Load environment variables
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
else
  echo "ERROR: The '.env' file is missing. Please create one with the required variables."
  echo "Refer to Step 1 & 2 of the README for guidance."
  exit 1
fi

# Validate environment variables
if [ -z "$DOMAIN_NAME" ]; then
  echo "ERROR: The 'DOMAIN_NAME' environment variable is not set in the '.env' file."
  echo "Please set it and try again."
  exit 1
fi

if [ -z "$LETSENCRYPT_MAIL" ]; then
  echo "ERROR: The 'LETSENCRYPT_MAIL' environment variable is not set in the '.env' file."
  echo "Please set it and try again."
  exit 1
fi

echo "Setting up certificates for the domain: $DOMAIN_NAME"
echo "Using the email address: $LETSENCRYPT_MAIL"

# Create necessary directories
mkdir -p ./data/certbot/conf/live/$DOMAIN_NAME
mkdir -p ./data/certbot/www

echo "Generating nginx configuration..."
cp nginx.conf.template nginx.conf
sed -i "s/example.com/$DOMAIN_NAME/g" nginx.conf

if [ -f ./htpasswd ]; then
  echo "INFO: 'htpasswd' file found. Enabling basic authentication in the nginx configuration."
  sed -i "s/##AUTH##/auth_basic \"Restricted Content\";\nauth_basic_user_file \/etc\/nginx\/htpasswd;/g" nginx.conf
else
  echo "WARNING: 'htpasswd' file was not found."
  echo "This will expose your services to the public without any authentication."
  echo "Otherwise, please create an 'htpasswd' file and place it in the current directory."
  echo "Check Step 4 of the README for guidance."
  read -p "Do you want to proceed without authentication? (y/n): " confirm_no_auth
  if [[ "$confirm_no_auth" != "y" ]]; then
    echo "Operation aborted by the user. Please provide an 'htpasswd' file and try again."
    exit 1
  fi
  echo "INFO: Proceeding without authentication as confirmed by the user."
  sed -i "s/##AUTH##//g" nginx.conf
fi

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