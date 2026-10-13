from datetime import datetime

from django.conf import settings
from django.db import models
from django.utils import timezone


def _current_local_time():
	return timezone.localtime(timezone.now()).time().replace(microsecond=0)

class SensorReading(models.Model):
	timestamp = models.DateTimeField(default = timezone.now)
	
	# Sensores genéricos - você pode adaptar aos seus sensores específicos
	sensor1 = models.FloatField()
	sensor2 = models.FloatField()
	sensor3 = models.FloatField()
	sensor4 = models.FloatField()
	sensor5 = models.FloatField()
	sensor6 = models.FloatField()
	sensor7 = models.FloatField()
	sensor8 = models.FloatField()
	sensor9 = models.FloatField()
	sensor10 = models.FloatField()
	sensor11 = models.FloatField()
	sensor12 = models.FloatField()
	sensor13 = models.FloatField()
	sensor14 = models.FloatField(null=True, blank=True)
	
	# Campos adicionais se necessário
	device_id = models.CharField(max_length = 50, blank = True, null = True)
	battery_level = models.FloatField(blank = True, null = True)
	
	def __str__(self):
		return f"{self.device_id} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
	
	class Meta:
		ordering = ['-timestamp']

class PerfilUsuario(models.Model):
	ROLE_IC = 'ic'
	ROLE_ADMIN = 'admin'
	ROLE_SUPERVISOR = 'supervisor'

	ROLE_CHOICES = (
		(ROLE_IC, 'IC / Estagiário / Aluno'),
		(ROLE_ADMIN, 'Administrador'),
		(ROLE_SUPERVISOR, 'Pós-Graduação / Coordenador / Supervisor'),
	)

	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfil')
	role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_IC)
	ativo = models.BooleanField(default=True)
	criado_em = models.DateTimeField(auto_now_add=True)
	atualizado_em = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"{self.user.username} - {self.get_role_display()}"

	def is_ic(self):
		return self.role == self.ROLE_IC

	def is_admin_like(self):
		return self.role in {self.ROLE_ADMIN, self.ROLE_SUPERVISOR}


# --- RFID Card Model ---
class CartaoRFID(models.Model):
	uid = models.CharField(max_length=50, unique=True, verbose_name="UID do Cartão")
	usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Dono do Cartão", null=True, blank=True)
	cadastrado_em = models.DateTimeField(auto_now_add=True, null=True, blank=True)

	def __str__(self):
		return f"{self.usuario.username if self.usuario else 'Sem dono'} - {self.uid}"


class AccessLog(models.Model):
	uid = models.CharField(max_length=32)
	autorizado = models.BooleanField()
	timestamp = models.DateTimeField(auto_now_add=True)
	cartao = models.ForeignKey(CartaoRFID, on_delete=models.SET_NULL, null=True, blank=True)

	def __str__(self):
		estado = 'Autorizado' if self.autorizado else 'Negado'
		return f"{self.uid} - {estado} - {self.timestamp}"


class RegistroPonto(models.Model):
	ENTRADA = 'ENTRADA'
	SAIDA = 'SAIDA'

	TIPO_CHOICES = (
		(ENTRADA, 'Entrada'),
		(SAIDA, 'Saída'),
	)

	cartao = models.ForeignKey(CartaoRFID, on_delete=models.CASCADE, related_name='registros')
	usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='registros_ponto', null=True, blank=True)
	nome_aluno = models.CharField(max_length=150, default='', blank=True)
	uid_tag = models.CharField(max_length=50, default='', blank=True)
	tipo_movimento = models.CharField(max_length=10, choices=TIPO_CHOICES, default=ENTRADA)
	timestamp = models.DateTimeField(default=timezone.now, db_index=True, verbose_name="Data/Hora da Batida")
	data_ponto = models.DateField(default=timezone.localdate, db_index=True)
	hora_ponto = models.TimeField(default=_current_local_time)
	observacao = models.TextField(blank=True)

	def save(self, *args, **kwargs):
		if self.timestamp:
			local_ts = timezone.localtime(self.timestamp)
			if not self.data_ponto:
				self.data_ponto = local_ts.date()
			if not self.hora_ponto:
				self.hora_ponto = local_ts.time().replace(microsecond=0)
		elif self.data_ponto and self.hora_ponto:
			combined = datetime.combine(self.data_ponto, self.hora_ponto)
			self.timestamp = timezone.make_aware(combined, timezone.get_current_timezone())

		if self.cartao_id:
			self.uid_tag = self.uid_tag or self.cartao.uid
			if not self.usuario_id and self.cartao.usuario_id:
				self.usuario = self.cartao.usuario

		if not self.nome_aluno and self.usuario_id:
			self.nome_aluno = self.usuario.get_full_name() or self.usuario.username

		super().save(*args, **kwargs)

	def __str__(self):
		return f"{self.nome_aluno} - {self.tipo_movimento} em {self.timestamp}"

	class Meta:
		ordering = ['-timestamp']

class BriseSensorReading(models.Model):
	"""Sensor readings for Brise Vegetal monitoring (6 DS18B20, 2 DHT11 (temp+hum), 2 UV, 2 anemometers)"""
	timestamp = models.DateTimeField(default=timezone.now)

	# DS18B20 (6)
	ds18b20_1 = models.FloatField(null=True, blank=True)
	ds18b20_2 = models.FloatField(null=True, blank=True)
	ds18b20_3 = models.FloatField(null=True, blank=True)
	ds18b20_4 = models.FloatField(null=True, blank=True)
	ds18b20_5 = models.FloatField(null=True, blank=True)
	ds18b20_6 = models.FloatField(null=True, blank=True)

	# DHT11 (2) - temp and humidity each
	dht11_1_temp = models.FloatField(null=True, blank=True)
	dht11_1_hum = models.FloatField(null=True, blank=True)
	dht11_2_temp = models.FloatField(null=True, blank=True)
	dht11_2_hum = models.FloatField(null=True, blank=True)

	# UV (2)
	uv_1 = models.FloatField(null=True, blank=True)
	uv_2 = models.FloatField(null=True, blank=True)

	# Anemometers (2)
	wind_1 = models.FloatField(null=True, blank=True)
	wind_2 = models.FloatField(null=True, blank=True)

	device_id = models.CharField(max_length=50, blank=True, null=True)
	battery_level = models.FloatField(blank=True, null=True)

	def __str__(self):
		return f"BRISE {self.device_id} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"

class PavimentosSensorReading(models.Model):
	"""Placeholder model for pavimentos monitoring sensors. Add fields as needed."""
	timestamp = models.DateTimeField(default=timezone.now)
	# Example fields; adjust later
	sensor_a = models.FloatField(null=True, blank=True)
	sensor_b = models.FloatField(null=True, blank=True)
	device_id = models.CharField(max_length=50, blank=True, null=True)
	battery_level = models.FloatField(blank=True, null=True)

	def __str__(self):
		return f"PAV {self.device_id} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
