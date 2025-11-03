import os
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.test import RequestFactory
from app.views import receive_sensor_data

rf = RequestFactory()
payload = {
    "monitoring": "brise",
    "device_id": "test_esp",
    "battery": 75.0,
    "ds18b20_1": 24.1,
    "ds18b20_2": 24.2,
    "ds18b20_3": 23.9,
    "ds18b20_4": 24.0,
    "ds18b20_5": 24.3,
    "ds18b20_6": 24.4,
    "dht11_1_temp": 23.5,
    "dht11_1_hum": 55.1,
    "dht11_2_temp": 23.0,
    "dht11_2_hum": 54.8,
    "uv_1": 0.12,
    "uv_2": 0.13,
    "wind_1": 1.2,
    "wind_2": 1.1,
}

req = rf.post('/api/receive/', json.dumps(payload), content_type='application/json')
resp = receive_sensor_data(req)
print('STATUS:', resp.status_code)
try:
    print('CONTENT:', resp.content.decode('utf-8'))
except Exception:
    print('CONTENT (binary):', resp.content)

