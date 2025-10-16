import json
import traceback
from datetime import timedelta
from venv import logger

from django import forms
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.db.models import Avg, Max, Min
from django.http import JsonResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_GET
from rest_framework.renderers import *
from rest_framework.request import *
from rest_framework.views import *

from config import settings
from .models import SensorReading, CartaoRFID, AccessLog
from django.views.decorators.csrf import csrf_exempt


class HomeView(LoginRequiredMixin, APIView):
    renderer_classes = [TemplateHTMLRenderer]
    template_name = 'home.html'
    login_url = 'login'

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

@require_GET
def latest_sensor_data(request):
    latest = SensorReading.objects.order_by('-timestamp').first()
    if not latest:
        return JsonResponse({'error': 'No data available'}, status=404)
    return JsonResponse({
        'sensor1': latest.sensor1,
        'sensor2': latest.sensor2,
        'timestamp': latest.timestamp.strftime('%H:%M'),
        'battery': latest.battery_level,
    })

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


class RegisterForm(forms.Form):
    first_name = forms.CharField(label='Nome', max_length=30)
    last_name = forms.CharField(label='Sobrenome', max_length=30)
    username = forms.CharField(label='Usuário', max_length=30)
    email = forms.EmailField(label='E-mail')
    password = forms.CharField(label='Senha', widget=forms.PasswordInput)
    group = forms.ChoiceField(label='Grupo', choices=[
        ('adm', 'Administrador'),
        ('ic', 'Iniciação Científica'),
        ('mestrado', 'Mestrado'),
        ('doutorado', 'Doutorado'),
        ('professor', 'Professor'),
    ])

def register_view(request):
    form = RegisterForm(request.POST or None)
    message = None
    if request.method == 'POST' and form.is_valid():
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        first_name = form.cleaned_data['first_name']
        last_name = form.cleaned_data['last_name']
        email = form.cleaned_data['email']
        group_name = form.cleaned_data['group']
        # Validação extra do email
        try:
            validate_email(email)
        except ValidationError:
            form.add_error('email', 'E-mail inválido.')
        else:
            if User.objects.filter(username=username).exists():
                form.add_error('username', 'Usuário já existe.')
            elif User.objects.filter(email=email).exists():
                form.add_error('email', 'E-mail já cadastrado.')
            else:
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    is_active=False
                )
                # Adiciona ao grupo
                group, created = Group.objects.get_or_create(name=group_name)
                user.groups.add(group)
                message = 'Cadastro realizado! Aguarde o administrador liberar seu acesso.'
    return render(request, 'register.html', {'form': form, 'message': message})

class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

def login_view(request):
    form = LoginForm(request.POST or None)
    error_message = None
    grupos_validos = ['adm', 'ic', 'mestrado', 'doutorado', 'professor']
    if request.method == 'POST' and form.is_valid():
        user = authenticate(request, username=form.cleaned_data['username'], password=form.cleaned_data['password'])
        if user is not None:
            if user.is_active:
                # Verifica se o usuário pertence a algum grupo válido
                if user.groups.filter(name__in=grupos_validos).exists():
                    login(request, user)
                    return redirect('home')
                else:
                    error_message = 'Seu usuário não pertence a nenhum grupo autorizado.'
            else:
                error_message = 'Seu cadastro ainda não foi autorizado pelo administrador.'
        else:
            error_message = 'Usuário ou senha inválidos.'
    return render(request, 'login.html', {'form': form, 'error_message': error_message})

@login_required(login_url='login')
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


@login_required(login_url='login')
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


@login_required(login_url='login')
def access_log_list(request):
    logs = AccessLog.objects.select_related('cartao').order_by('-timestamp')
    paginator = Paginator(logs, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'access_log_list.html', {'page_obj': page_obj})

class CartaoRFIDForm(forms.ModelForm):
    class Meta:
        model = CartaoRFID
        fields = ['uid', 'nome', 'nome_pessoa', 'email', 'funcao', 'matricula']
        labels = {
            'uid': 'UID do Cartão',
            'nome': 'Nome do Cartão (opcional)',
            'nome_pessoa': 'Nome da Pessoa',
            'email': 'E-mail',
            'funcao': 'Função',
            'matricula': 'Matrícula',
        }

@login_required(login_url='login')
def cadastrar_cartao(request):
    form = CartaoRFIDForm(request.POST or None)
    message = None
    if request.method == 'POST' and form.is_valid():
        form.save()
        message = 'Cartão cadastrado com sucesso!'
        form = CartaoRFIDForm()  # Limpa o formulário
    return render(request, 'cadastrar_cartao.html', {'form': form, 'message': message})

#====== LOGIN FORM ======#
class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)
    
#====== LOGIN ======#
def login_view(request):
    form = LoginForm(request.POST or None)
    error_message = None
    grupos_validos = ['adm', 'ic', 'mestrado', 'doutorado', 'professor']
    if request.method == 'POST' and form.is_valid():
        user = authenticate(request, username=form.cleaned_data['username'], password=form.cleaned_data['password'])
        if user is not None:
            if user.is_active:
                # Verifica se o usuário pertence a algum grupo válido
                if user.groups.filter(name__in=grupos_validos).exists():
                    login(request, user)
                    return redirect('home')
                else:
                    error_message = 'Seu usuário não pertence a nenhum grupo autorizado.'
            else:
                error_message = 'Seu cadastro ainda não foi autorizado pelo administrador.'
        else:
            error_message = 'Usuário ou senha inválidos.'
    return render(request, 'login.html', {'form': form, 'error_message': error_message})
#====== LOGOUT ======#
def logout_view(request):
    logout(request)
    return redirect('login')

@csrf_exempt  # Para facilitar testes com ESP, ideal usar autenticação depois
def verifica_cartao(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            uid = data.get("uid")
            cartao = CartaoRFID.objects.filter(uid=uid).first()
            autorizado = cartao is not None
            # Registra o acesso
            AccessLog.objects.create(uid=uid, cartao=cartao, autorizado=autorizado)
            return JsonResponse({"autorizado": autorizado})
        except Exception as e:
            return JsonResponse({"erro": str(e)}, status=400)
    return JsonResponse({"erro": "Método não permitido"}, status=405)

def dashboard_project(request, project):
    # Exemplo simples, ajuste conforme sua lógica
    return render(request, 'dashboard.html', {'project': project})

def data_table_project(request, project):
    # Exemplo simples, ajuste conforme sua lógica
    return render(request, 'data_table.html', {'project': project})
