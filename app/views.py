import json
import traceback
from datetime import timedelta
from venv import logger

from django.core.paginator import Paginator
from django.db.models import Avg, Max, Min
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from rest_framework.renderers import *
from rest_framework.request import *
from rest_framework.views import *

from config import settings
from .models import SensorReading


class HomeView(APIView):
    renderer_classes = [TemplateHTMLRenderer]
    template_name = 'base.html'

    def get(self, request):
        context = {
            'title': 'Sensor Monitoring System',
            'description': 'Welcome to the sensor data monitoring platform',
            'features': [
                'Real-time sensor data visualization',
                'Historical data analysis',
                'Device management',
                'API endpoints for integration'
            ],
            'api_endpoints': [
                {'name': 'Sensor Data API', 'url': '/api/receive/', 'method': 'POST'},
                {'name': 'Dashboard', 'url': '/dashboard/', 'method': 'GET'},
                {'name': 'Data Table', 'url': '/table/', 'method': 'GET'}
            ]
        }
        return Response(context, status=status.HTTP_200_OK)
@csrf_exempt
def receive_sensor_data(request):
    """
    API endpoint to receive sensor data from ESP32 devices
    Expected JSON format:
    {
        "sensor1": value, "sensor2": value, ..., "sensor13": value,
        "device_id": string,
        "battery": float (0-100)
    }
    """
    if request.method != 'POST':
        return JsonResponse(
                {'status': 'error', 'message': 'Only POST method is allowed'},
                status = 405
                )
    
    try:
        # Parse and validate JSON data
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            return JsonResponse(
                    {'status': 'error', 'message': 'Invalid JSON format'},
                    status = 400
                    )
        
        # Validate required fields
        required_fields = [f'sensor{i}' for i in range(1, 14)] + ['device_id']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return JsonResponse(
                    {'status': 'error', 'message': f'Missing required fields: {", ".join(missing_fields)}'},
                    status = 400
                    )
        
        # Validate sensor values
        try:
            sensor_data = {
                    f'sensor{i}': float(data[f'sensor{i}'])
                    for i in range(1, 14)
                    }
        except (ValueError, TypeError):
            return JsonResponse(
                    {'status': 'error', 'message': 'All sensor values must be numbers'},
                    status = 400
                    )
        
        # Validate battery level
        battery_level = float(data.get('battery', 0))
        if not 0 <= battery_level <= 100:
            return JsonResponse(
                    {'status': 'error', 'message': 'Battery level must be between 0 and 100'},
                    status = 400
                    )
        
        # Create and save new reading
        reading = SensorReading(
                timestamp = timezone.now(),
                device_id = data['device_id'],
                battery_level = battery_level,
                **sensor_data
                )
        reading.save()
        
        return JsonResponse({
                'status': 'success',
                'message': 'Data saved successfully',
                'reading_id': reading.id,
                'timestamp': reading.timestamp.isoformat()
                })
    
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error processing sensor data: {str(e)}", exc_info = True)
        
        return JsonResponse(
                {'status': 'error', 'message': 'Internal server error'},
                status = 500
                )

def dashboard(request):
    """
    Dashboard view showing charts and summary of last 24 hours
    """
    try:
        # Get data from last 24 hours
        time_threshold = timezone.now() - timedelta(hours=24)
        readings = SensorReading.objects.filter(
            timestamp__gte=time_threshold
        ).order_by('timestamp')
        
        # Get summary statistics
        summary = {
                'temperature': {
                        'current': readings.last().sensor1 if readings.exists() else None,
                        'avg': readings.aggregate(Avg('sensor1'))['sensor1__avg'],
                        'max': readings.aggregate(Max('sensor1'))['sensor1__max'],
                        'min': readings.aggregate(Min('sensor1'))['sensor1__min']
                        },
                'humidity': {
                        'current': readings.last().sensor7 if readings.exists() else None,
                        'avg': readings.aggregate(Avg('sensor7'))['sensor7__avg'],
                        'max': readings.aggregate(Max('sensor7'))['sensor7__max'],
                        'min': readings.aggregate(Min('sensor7'))['sensor7__min']
                        },
                'battery': {
                        'current': readings.last().battery_level if readings.exists() else None,
                        'avg': readings.aggregate(Avg('battery_level'))['battery_level__avg'],
                        'min': readings.aggregate(Min('battery_level'))['battery_level__min']
                        }
                }
        
        context = {
                'readings': readings,
                'summary': summary,
                'sensor_names': {
                        1: "Temperatura Externa 1",
                        2: "Temperatura Externa 2",
                        3: "Temperatura Solo 1",
                        4: "Temperatura Solo 2",
                        5: "Temperatura Ar 1",
                        6: "Temperatura Ar 2",
                        7: "Umidade Ar 1",
                        8: "Umidade Ar 2",
                        9: "Umidade Solo",
                        10: "Radiação UV 1",
                        11: "Radiação UV 2",
                        12: "Velocidade Vento 1",
                        13: "Velocidade Vento 2"
                        },
                'units': {
                        1: "°C", 2: "°C", 3: "°C", 4: "°C", 5: "°C", 6: "°C",
                        7: "%", 8: "%", 9: "%",
                        10: "UV", 11: "UV",
                        12: "m/s", 13: "m/s"
                        }
                }
        return render(request, 'dashboard.html', context)
    
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in dashboard view: {str(e)}", exc_info = True)
        return render(request, 'error.html', {'error': str(e)})


def data_table(request):
	"""
	View showing paginated table with all sensor readings
	"""
	try:
		all_readings = SensorReading.objects.all().order_by('-timestamp')
		
		# Pagination - 50 items per page
		paginator = Paginator(all_readings, 50)
		page_number = request.GET.get('page')
		page_obj = paginator.get_page(page_number)
		
		context = {
				'page_obj': page_obj,
				'sensor_names': {
						1: "Temp 1", 2: "Temp 2", 3: "Temp 3", 4: "Temp 4",
						5: "Temp 5", 6: "Temp 6", 7: "Hum 1", 8: "Hum 2",
						9: "Hum 3", 10: "UV 1", 11: "UV 2", 12: "Vento 1",
						13: "Vento 2"
						},
				'units': {
						1: "°C", 2: "°C", 3: "°C", 4: "°C", 5: "°C", 6: "°C",
						7: "%", 8: "%", 9: "%",
						10: "UV", 11: "UV",
						12: "m/s", 13: "m/s"
						}
				}
		return render(request, 'data_table.html', context)
	
	except Exception as e:
		import logging
		logger = logging.getLogger(__name__)
		logger.error(f"Error in data_table view: {str(e)}", exc_info = True)
		return render(request, 'error.html', {'error': str(e)})


def custom_error_view(request, exception = None):
	"""
	Custom error view that shows detailed technical information for debugging,
	while maintaining a user-friendly interface.
	"""
	# Get exception information
	exc_type, exc_value, exc_traceback = sys.exc_info()
	error_traceback = traceback.format_exception(exc_type, exc_value, exc_traceback)
	
	# Build context with detailed error information
	context = {
			'error_type': exc_type.__name__ if exc_type else 'Unknown Error',
			'error_message': str(exc_value) if exc_value else 'No error message available',
			'error_traceback': error_traceback,
			'timestamp': timezone.now(),
			'request_path': request.path,
			'request_method': request.method,
			'debug_mode': settings.DEBUG,
			}
	
	# Add additional debug information if in DEBUG mode
	if settings.DEBUG:
		from django.http import QueryDict
		context.update({
				'request_headers': dict(request.headers),
				'request_params': QueryDict(request.META.get('QUERY_STRING', '')),
				'request_post': request.POST if request.method == 'POST' else None,
				})
	
	# Determine the status code
	status_code = 500
	if hasattr(exception, 'status_code'):
		status_code = exception.status_code
	context['status_code'] = status_code
	
	# Log the error
	logger.error(
			f"Error {status_code} at {request.path}\n"
			f"Type: {context['error_type']}\n"
			f"Message: {context['error_message']}\n"
			f"Traceback:\n{''.join(error_traceback)}"
			)
	
	return render(request, 'error.html', context, status = status_code)