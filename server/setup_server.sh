#!/bin/bash

set -e

APP_NAME="benchmark_server"
SERVICE_FILE="./benchmark_server.service"
SYSTEMD_SERVICE_FILE="/etc/systemd/system/$APP_NAME.service"

# Load environment variables from .env file in project root directory
source ./benchmark_server/.env

# Update and install system dependencies
dnf update -y
dnf install -y python3 virtualenv

cd "${APP_NAME}"

# Create virtual environment if it doesn't exist
if [ ! -d "./benchmark_venv" ]; then
    python3 -m venv benchmark_venv
fi

# install python virtual enviroment dependencies
./benchmark_venv/bin/python3 -m pip install --upgrade pip
./benchmark_venv/bin/python3 -m pip install pandas flask gunicorn python-dotenv

cp "$SERVICE_FILE" "$SYSTEMD_SERVICE_FILE"

# Set SELinux to Permissive Mode
sudo setenforce 0

# Configure the firewall to allow the specified port
firewall-cmd --permanent --add-port="${PORT}/tcp"
firewall-cmd --reload

### Service start:

# Reload systemd to recognize the new service
systemctl daemon-reload

# Enable and start the service
systemctl enable benchmark_server
systemctl start benchmark_server

echo "Flask application is running and accessible on port $PORT."
