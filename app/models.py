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
	
	# Campos adicionais se necessário
	device_id = models.CharField(max_length = 50, blank = True, null = True)
	battery_level = models.FloatField(blank = True, null = True)
	
	def __str__(self):
		return f"Leitura em {self.timestamp}"
	
	class Meta:
		ordering = ['-timestamp']