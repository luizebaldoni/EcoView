from django.contrib import admin

from .models import AccessLog, BriseSensorReading, CartaoRFID, PerfilUsuario, PavimentosSensorReading, RegistroPonto, SensorReading


admin.site.register(PerfilUsuario)
admin.site.register(CartaoRFID)
admin.site.register(AccessLog)
admin.site.register(RegistroPonto)
admin.site.register(SensorReading)
admin.site.register(BriseSensorReading)
admin.site.register(PavimentosSensorReading)
