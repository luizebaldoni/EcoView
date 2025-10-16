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
