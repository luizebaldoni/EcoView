import json

from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import SensorReading


@csrf_exempt
def receive_sensor_data(request):
	if request.method == 'POST':
		try:
			data = json.loads(request.body)
			
			# Criar nova leitura
			reading = SensorReading(
					timestamp = timezone.now(),
					sensor1 = data.get('sensor1'),
					sensor2 = data.get('sensor2'),
					sensor3 = data.get('sensor3'),
					sensor4 = data.get('sensor4'),
					sensor5 = data.get('sensor5'),
					sensor6 = data.get('sensor6'),
					sensor7 = data.get('sensor7'),
					sensor8 = data.get('sensor8'),
					sensor9 = data.get('sensor9'),
					sensor10 = data.get('sensor10'),
					sensor11 = data.get('sensor11'),
					sensor12 = data.get('sensor12'),
					sensor13 = data.get('sensor13'),
					device_id = data.get('device_id'),
					battery_level = data.get('battery'),
					)
			reading.save()
			
			return JsonResponse({'status': 'success', 'message': 'Data saved successfully'})
		
		except Exception as e:
			return JsonResponse({'status': 'error', 'message': str(e)}, status = 400)
	
	return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status = 405)

def dashboard(request):
	# Pegar as últimas 24 horas de dados
	from django.utils import timezone
	from datetime import timedelta
	
	time_threshold = timezone.now() - timedelta(hours = 24)
	readings = SensorReading.objects.filter(timestamp__gte = time_threshold).order_by('timestamp')
	
	# Preparar dados para os gráficos
	timestamps = [reading.timestamp.strftime("%H:%M") for reading in readings]
	sensor_data = {
			'sensor1': [reading.sensor1 for reading in readings],
			# Adicione outros sensores conforme necessário
			}
	
	context = {
			'readings': readings[:10],  # Últimas 10 leituras para a tabela
			'timestamps': timestamps,
			'sensor_data': sensor_data,
			}
	return render(request, 'dashboard.html', context)


def data_table(request):
	all_readings = SensorReading.objects.all().order_by('-timestamp')
	
	# Paginação
	paginator = Paginator(all_readings, 50)  # 50 leituras por página
	page_number = request.GET.get('page')
	page_obj = paginator.get_page(page_number)
	
	return render(request, 'data_table.html', {'page_obj': page_obj})