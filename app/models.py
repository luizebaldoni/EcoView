from django.db import models
from django.utils import timezone

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

# --- RFID Card Model ---
class CartaoRFID(models.Model):
	uid = models.CharField(max_length=32, unique=True)
	nome = models.CharField(max_length=100, blank=True)
	nome_pessoa = models.CharField(max_length=100)
	email = models.EmailField()
	funcao = models.CharField(max_length=100)
	matricula = models.CharField(max_length=50)

	def __str__(self):
		return f"{self.nome_pessoa} - {self.uid}" if self.nome_pessoa else self.uid

class AccessLog(models.Model):
	uid = models.CharField(max_length=32)
	cartao = models.ForeignKey(CartaoRFID, null=True, blank=True, on_delete=models.SET_NULL)
	autorizado = models.BooleanField()
	timestamp = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		status = "Autorizado" if self.autorizado else "Negado"
		return f"{self.uid} - {status} em {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"

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
