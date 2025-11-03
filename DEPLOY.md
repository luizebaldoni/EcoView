# Deploy & DB setup for EcoView

This file documents the steps to configure multiple Postgres DBs and run migrations for the EcoView project.

Overview
- The project supports multiple databases: `default`, `brise`, `pavimentos`.
- Use environment variables to point each DB to the desired Postgres instance.

Environment variables (examples)
- DATABASE_URL (optional): postgres://user:pass@host:port/dbname for default
- DATABASE_URL_BRISE: postgres://user:pass@host:port/ecoview_db  (used by `BriseSensorReading`)
- DATABASE_URL_PAVIMENTOS: postgres://user:pass@host:port/pavimentos_db
- DJANGO_SECRET_KEY, DJANGO_DEBUG, DJANGO_ALLOWED_HOSTS as usual

Example steps on the server (bash)
1) Install dependencies (virtualenv activated):

```bash
pip install -r requirements.txt
```

2) Export DB env vars (example)

```bash
export DATABASE_URL='postgres://eco_user:secret@127.0.0.1:5432/eco_default'
export DATABASE_URL_BRISE='postgres://eco_user:secret@127.0.0.1:5432/ecoview_db'
export DATABASE_URL_PAVIMENTOS='postgres://eco_user:secret@127.0.0.1:5432/eco_pavimentos'
export DJANGO_SECRET_KEY='changeme'
export DJANGO_DEBUG='False'
```

3) Run migrations (router directs models to correct DBs):

```bash
python manage.py migrate --database=default
python manage.py migrate --database=brise
python manage.py migrate --database=pavimentos
```

4) Test inserting data (curl example for brise):

```bash
curl -X POST http://127.0.0.1:8000/api/receive/ \
 -H "Content-Type: application/json" \
 -d '{"monitoring":"brise","device_id":"esp01","battery":85, "ds18b20_1":24.1, "ds18b20_2":24.2, "ds18b20_3":23.9, "ds18b20_4":24.0, "ds18b20_5":24.3, "ds18b20_6":24.4, "dht11_1_temp":23.5, "dht11_1_hum":55.1, "dht11_2_temp":23.0, "dht11_2_hum":54.8, "uv_1":0.12, "uv_2":0.13, "wind_1":1.2, "wind_2":1.1}'
```

Notes
- Back up DBs before running migrations in production.
- Secure the receive endpoint (currently CSRF exempt). Consider HMAC or token-based auth.
- If a DB does not exist or env vars are not set, `migrate --database=brise` will fail.

If you want, I can also add a small script to run these steps automatically (checks for DB existence first).
