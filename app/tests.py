from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from .models import BriseSensorReading, CartaoRFID, PerfilUsuario, RegistroPonto

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
        self.assertEqual(BriseSensorReading.objects.using('default').count(), 1)
        r = BriseSensorReading.objects.using('default').first()
        self.assertEqual(r.device_id, 'test_esp')
        self.assertAlmostEqual(r.ds18b20_1, 24.1)
        self.assertAlmostEqual(r.dht11_1_hum, 55.1)
class TestPointWorkflow(TestCase):
    def setUp(self):
        self.client = Client()
        self.ic_group = Group.objects.create(name='ic')
        self.adm_group = Group.objects.create(name='adm')

        self.ic_user = User.objects.create_user(username='ic_user', password='secret123', first_name='IC', last_name='Aluno')
        self.ic_user.groups.add(self.ic_group)
        PerfilUsuario.objects.create(user=self.ic_user, role=PerfilUsuario.ROLE_IC)

        self.other_user = User.objects.create_user(username='outro_user', password='secret123', first_name='Outro', last_name='Aluno')
        self.other_user.groups.add(self.ic_group)
        PerfilUsuario.objects.create(user=self.other_user, role=PerfilUsuario.ROLE_IC)

        self.admin_user = User.objects.create_user(username='admin_user', password='secret123', first_name='Admin', last_name='User')
        self.admin_user.groups.add(self.adm_group)
        PerfilUsuario.objects.create(user=self.admin_user, role=PerfilUsuario.ROLE_ADMIN)

        self.ic_card = CartaoRFID.objects.create(uid='ABC123', usuario=self.ic_user)
        self.other_card = CartaoRFID.objects.create(uid='XYZ789', usuario=self.other_user)

        self.receive_url = reverse('registrar_ponto_rfid')
        self.dashboard_url = reverse('ponto_dashboard')
        self.export_url = reverse('exportar_relatorio_ponto')

    def _create_manual_record(self, user, card, tipo, minutes_offset=0):
        ts = timezone.now() + timedelta(minutes=minutes_offset)
        return RegistroPonto.objects.create(
            cartao=card,
            usuario=user,
            nome_aluno=user.get_full_name() or user.username,
            uid_tag=card.uid,
            tipo_movimento=tipo,
            timestamp=ts,
            data_ponto=ts.date(),
            hora_ponto=ts.time().replace(microsecond=0),
        )

    def test_registrar_ponto_alterna_entrada_saida(self):
        response1 = self.client.post(self.receive_url, data='ABC123', content_type='text/plain')
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(RegistroPonto.objects.count(), 1)
        self.assertEqual(RegistroPonto.objects.first().tipo_movimento, RegistroPonto.ENTRADA)

        response2 = self.client.post(self.receive_url, data='ABC123', content_type='text/plain')
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(RegistroPonto.objects.count(), 2)
        self.assertEqual(RegistroPonto.objects.order_by('-timestamp').first().tipo_movimento, RegistroPonto.SAIDA)

    def test_ic_only_sees_own_records_in_dashboard(self):
        self._create_manual_record(self.ic_user, self.ic_card, RegistroPonto.ENTRADA, minutes_offset=-90)
        self._create_manual_record(self.ic_user, self.ic_card, RegistroPonto.SAIDA, minutes_offset=-30)
        self._create_manual_record(self.other_user, self.other_card, RegistroPonto.ENTRADA, minutes_offset=-120)

        self.client.force_login(self.ic_user)
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.ic_user.get_full_name())
        self.assertNotContains(response, self.other_user.get_full_name())

    def test_admin_can_export_csv(self):
        self._create_manual_record(self.ic_user, self.ic_card, RegistroPonto.ENTRADA, minutes_offset=-90)
        self._create_manual_record(self.other_user, self.other_card, RegistroPonto.ENTRADA, minutes_offset=-120)

        self.client.force_login(self.admin_user)
        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        content = response.content.decode('utf-8')
        self.assertIn(self.ic_user.get_full_name(), content)
        self.assertIn(self.other_user.get_full_name(), content)

