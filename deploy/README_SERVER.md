Server deployment checklist for EcoView

1) Pull latest code to server
   git pull origin main

2) Create virtualenv and install requirements
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

3) Create/copy .env file
   cp .env.example .env
   Edit .env with real secrets and DB URLs

4) Create DBs and user (example PostgreSQL)
   sudo -u postgres createuser -P ecotec_deploy_user
   sudo -u postgres createdb -O ecotec_deploy_user ecoview_db
   sudo -u postgres createdb -O ecotec_deploy_user ecoview_pavimentos

5) Run migrations
   export DJANGO_SETTINGS_MODULE=config.settings
   python manage.py migrate --database=default
   python manage.py migrate --database=brise
   python manage.py migrate --database=pavimentos

6) Collect static
   python manage.py collectstatic --noinput

7) Configure Gunicorn systemd unit
   Copy deploy/gunicorn.service -> /etc/systemd/system/gunicorn-ecoview.service
   systemctl daemon-reload
   systemctl enable --now gunicorn-ecoview

8) Configure nginx
   Copy deploy/nginx_ecoview.conf -> /etc/nginx/sites-available/ecoview
   ln -s /etc/nginx/sites-available/ecoview /etc/nginx/sites-enabled/
   nginx -t
   systemctl restart nginx

9) Check logs and test endpoint
   tail -f /var/www/ecoview/logs/django.log
   curl -X GET http://127.0.0.1:8000/api/latest/

Notes:
 - This is a minimal guide. Adjust user/paths/ports for your setup. Secure secrets using a secrets manager if possible.

