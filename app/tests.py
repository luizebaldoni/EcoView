from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.conf import settings as djsettings
from .models import BriseSensorReading

# Ensure test DB has aliases for 'brise' and 'pavimentos' pointing to default test DB
_test_databases = dict(djsettings.DATABASES)
_test_databases['brise'] = _test_databases['default']
_test_databases['pavimentos'] = _test_databases['default']


@override_settings(DATABASES=_test_databases)
class TestReceiveSensorData(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('receive_sensor_data')

    def test_brise_named_payload_creates_record(self):
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
        response = self.client.post(self.url, data=payload, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(BriseSensorReading.objects.count(), 1)
        r = BriseSensorReading.objects.first()
        self.assertEqual(r.device_id, 'test_esp')
        self.assertAlmostEqual(r.ds18b20_1, 24.1)
        self.assertAlmostEqual(r.dht11_1_hum, 55.1)
