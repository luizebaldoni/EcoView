#!/usr/bin/env bash
# Server setup helper for EcoView (Ubuntu)
# USAGE: edit variables below, upload to server, run as root or with sudo
# NOTE: This script contains placeholders; review before running in production.

set -euo pipefail

# === Edit these variables before running ===
PROJECT_DIR=/var/www/ecoview        # path where repo is checked out
PYTHON_BIN=/usr/bin/python3
VENV_DIR=$PROJECT_DIR/venv
SERVICE_USER=www-data
SERVICE_GROUP=www-data
DB_SUPERUSER=postgres
DB_APP_USER=ecotec_deploy_user
DB_APP_PASS="CHANGE_ME_PASSWORD"
DB_DEFAULT=ecoview_default
DB_BRICE=ecoview_db
DB_PAV=ecoview_pavimentos
DOMAIN_OR_IP=10.5.1.100
# ==========================================

if [ "$EUID" -ne 0 ]; then
  echo "Run as root (sudo)"
  exit 1
fi

apt update
apt install -y python3-venv python3-pip python3-dev build-essential libpq-dev \
               postgresql postgresql-contrib nginx git curl

# Create system user if not exists
if ! id -u $SERVICE_USER >/dev/null 2>&1; then
  useradd --system --create-home --shell /bin/bash $SERVICE_USER || true
fi

# Create directories and ensure ownership
mkdir -p $PROJECT_DIR
chown -R $SERVICE_USER:$SERVICE_GROUP $PROJECT_DIR

# PostgreSQL: create DB user and DBs (adjust names as needed)
sudo -u $DB_SUPERUSER psql -v ON_ERROR_STOP=1 <<-SQL || true
DO
\$do\
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${DB_APP_USER}') THEN
      CREATE ROLE ${DB_APP_USER} LOGIN PASSWORD '${DB_APP_PASS}';
   END IF;
END
\$do\;
SQL

sudo -u $DB_SUPERUSER psql -v ON_ERROR_STOP=1 <<-SQL || true
CREATE DATABASE ${DB_BRICE} OWNER ${DB_APP_USER};
CREATE DATABASE ${DB_PAV} OWNER ${DB_APP_USER};
SQL

# Create python venv and install requirements
if [ ! -d "$VENV_DIR" ]; then
  sudo -u $SERVICE_USER $PYTHON_BIN -m venv $VENV_DIR
fi

# Activate venv and install
export PATH="$VENV_DIR/bin:$PATH"
pip install --upgrade pip
pip install -r $PROJECT_DIR/requirements.txt

# Create .env file (example) - DO NOT store secrets in plain files for production
cat > $PROJECT_DIR/.env <<EOF
# Copy and edit these values
DJANGO_SECRET_KEY='CHANGE_ME'
DJANGO_DEBUG='False'
DJANGO_ALLOWED_HOSTS='$DOMAIN_OR_IP'
DATABASE_URL='postgres://${DB_APP_USER}:${DB_APP_PASS}@localhost:5432/${DB_DEFAULT}'
DATABASE_URL_BRISE='postgres://${DB_APP_USER}:${DB_APP_PASS}@localhost:5432/${DB_BRICE}'
DATABASE_URL_PAVIMENTOS='postgres://${DB_APP_USER}:${DB_APP_PASS}@localhost:5432/${DB_PAV}'
EOF
chown $SERVICE_USER:$SERVICE_GROUP $PROJECT_DIR/.env
chmod 640 $PROJECT_DIR/.env

# Run migrations using the venv python
export DJANGO_SETTINGS_MODULE=config.settings
export PATH="$VENV_DIR/bin:$PATH"
cd $PROJECT_DIR
# Apply default then specific DB migrations (router will route models)
python manage.py migrate --database=default || true
python manage.py migrate --database=brise || true
python manage.py migrate --database=pavimentos || true

# Collect static
python manage.py collectstatic --noinput || true

# Create runtime dir for socket
mkdir -p /run/gunicorn
chown $SERVICE_USER:$SERVICE_GROUP /run/gunicorn

echo "Server setup script finished. Review outputs above for errors."

