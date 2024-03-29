#!/bin/bash

# Example script to:  
# 1. Run the app with gunicorn
# 2. Setup a systemd service for the gunicorn app
# 3. Setup Nginx as a reverse proxy to the gunicorn app

# First, find out the WiFi interface and IP address for configuring DOMAIN variable.
# WIFI_INTERFACE=$(networksetup -listallhardwareports | awk '/Wi-Fi|Airport/{getline; print $2}') #<- for Mac!
WIFI_INTERFACE=$(ip link | awk -F: '$0 !~ "lo|vir|docker|^[^0-9]"{print $2;getline}' | xargs)
LOCAL_IP=$(ip addr show $WIFI_INTERFACE | grep "inet\b" | awk '{print $2}' | cut -d/ -f1 | head -n 1)

# Define variables
APP_NAME="SeeMP"
USER=$(whoami)  # The current user
GROUP=$(id -gn $USER)  # The primary group of the current user
WORKING_DIRECTORY="$HOME/$APP_NAME"
VENV_PATH="$WORKING_DIRECTORY/venv"
SOCK_FILE="$WORKING_DIRECTORY/$APP_NAME.sock"
GUNICORN_PATH="$VENV_PATH/bin/gunicorn"
SERVICE_FILE="/etc/systemd/system/$APP_NAME.service"
DOMAIN=$LOCAL_IP  # Use the local machine's network IP for broader network access

# Ensure working directory exists and navigate there
mkdir -p $WORKING_DIRECTORY
cd $WORKING_DIRECTORY || exit

# Step 1: Setup the environment and dependencies
echo "Setting up the environment..."
sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-venv nginx ufw

# Set up Python virtual environment and install dependencies
python3 -m venv $VENV_PATH
source $VENV_PATH/bin/activate
pip install flask gunicorn

# Clone or copy your Flask app into $WORKING_DIRECTORY here if needed

# Step 2: Configure firewall (UFW)
echo "Configuring UFW firewall..."
sudo ufw allow 'Nginx Full'
sudo ufw allow ssh
sudo ufw --force enable

# Step 3: Setup Gunicorn with Systemd
echo "Creating Systemd service file for $APP_NAME..."
sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=Gunicorn instance to serve $APP_NAME
After=network.target

[Service]
User=$USER
Group=$GROUP
WorkingDirectory=$WORKING_DIRECTORY
Environment="PATH=$VENV_PATH/bin"
ExecStart=$GUNICORN_PATH --workers 4 --bind unix:$SOCK_FILE -m 007 -k gevent endpoint:app

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable $APP_NAME
sudo systemctl start $APP_NAME

# Step 4: Setup Nginx as a reverse proxy
echo "Creating Nginx configuration for $APP_NAME..."
sudo tee $NGINX_CONF > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        include proxy_params;
        proxy_pass http://unix:$SOCK_FILE;
    }
}
EOF

sudo ln -sfn $NGINX_CONF $NGINX_CONF_LINK
sudo nginx -t && sudo systemctl reload nginx

echo "$APP_NAME is now set up and available at http://$DOMAIN"
