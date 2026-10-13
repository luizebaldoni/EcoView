import calendar
import csv
import json
import logging
import sys
import traceback
from collections import defaultdict
from datetime import datetime, timedelta
from functools import wraps

from django import forms
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.db.models import Avg, Max, Min
from django.db import transaction
from django.db.utils import ConnectionDoesNotExist
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_GET
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt

from config import settings
from django.conf import settings as django_settings
from .models import *


IC_GROUPS = {'ic'}
ADMIN_GROUPS = {'adm', 'mestrado', 'doutorado', 'professor'}
AUTHORIZED_GROUPS = IC_GROUPS | ADMIN_GROUPS


def _user_group_names(user):
  if not user.is_authenticated:
    return set()
  return set(user.groups.values_list('name', flat=True))


def _profile_role(user):
  perfil = getattr(user, 'perfil', None)
  if perfil:
    return perfil.role
  return None


def user_is_ic(user):
  if not user.is_authenticated:
    return False
  if user.is_staff or user.is_superuser:
    return False
  return _profile_role(user) == PerfilUsuario.ROLE_IC or bool(_user_group_names(user) & IC_GROUPS)


def user_is_admin_like(user):
  if not user.is_authenticated:
    return False
  if user.is_staff or user.is_superuser:
    return True
  return _profile_role(user) in {PerfilUsuario.ROLE_ADMIN, PerfilUsuario.ROLE_SUPERVISOR} or bool(_user_group_names(user) & ADMIN_GROUPS)


def user_is_authorized_for_login(user):
  if not user.is_authenticated:
    return False
  if not user.is_active:
    return False
  if user.is_staff or user.is_superuser:
    return True
  if _profile_role(user) in {PerfilUsuario.ROLE_IC, PerfilUsuario.ROLE_ADMIN, PerfilUsuario.ROLE_SUPERVISOR}:
    return True
  return bool(_user_group_names(user) & AUTHORIZED_GROUPS)


def _permission_denied(request, message='Você não tem permissão para acessar esta área.'):
  return render(request, 'error.html', {'error': message, 'status_code': 403}, status=403)


def _format_seconds(total_seconds):
  total_seconds = int(total_seconds or 0)
  hours, remainder = divmod(total_seconds, 3600)
  minutes = remainder // 60
  return f'{hours:02d}:{minutes:02d}'


def _build_point_filters(request, queryset, allow_admin_filters=False):
  data_exata = parse_date(request.GET.get('data') or '')
  inicio = parse_date(request.GET.get('inicio') or '')
  fim = parse_date(request.GET.get('fim') or '')
  periodo = (request.GET.get('periodo') or '').lower()
  aluno_id = request.GET.get('aluno') if allow_admin_filters else None

  if data_exata:
    queryset = queryset.filter(data_ponto=data_exata)

  if inicio and fim:
    queryset = queryset.filter(data_ponto__range=(inicio, fim))
  elif periodo in {'semana', 'semanal'}:
    base = data_exata or timezone.localdate()
    inicio_semana = base - timedelta(days=base.weekday())
    fim_semana = inicio_semana + timedelta(days=6)
    queryset = queryset.filter(data_ponto__range=(inicio_semana, fim_semana))
  elif periodo in {'mes', 'mensal'}:
    base = data_exata or timezone.localdate()
    inicio_mes = base.replace(day=1)
    ultimo_dia = calendar.monthrange(base.year, base.month)[1]
    fim_mes = base.replace(day=ultimo_dia)
    queryset = queryset.filter(data_ponto__range=(inicio_mes, fim_mes))

  if aluno_id:
    queryset = queryset.filter(usuario_id=aluno_id)

  return queryset


def _calculate_worked_seconds(records):
  entrada_aberta = None
  total_seconds = 0
  for registro in sorted(records, key=lambda item: item.timestamp):
    if registro.tipo_movimento == RegistroPonto.ENTRADA:
      entrada_aberta = registro
    elif registro.tipo_movimento == RegistroPonto.SAIDA and entrada_aberta:
      total_seconds += max(0, int((registro.timestamp - entrada_aberta.timestamp).total_seconds()))
      entrada_aberta = None
  return total_seconds


def _aggregate_totals_by_user(records):
  groups = defaultdict(list)
  for registro in records:
    groups[registro.usuario_id].append(registro)

  result = []
  for usuario_id, itens in groups.items():
    usuario = itens[0].usuario or (itens[0].cartao.usuario if itens[0].cartao_id else None)
    total_seconds = _calculate_worked_seconds(itens)
    result.append({
      'usuario': usuario,
      'usuario_id': usuario_id,
      'nome': itens[0].nome_aluno if itens else (usuario.get_full_name() or usuario.username if usuario else 'Sem nome'),
      'total_seconds': total_seconds,
      'total_hhmm': _format_seconds(total_seconds),
      'total_decimal': round(total_seconds / 3600, 2),
    })

  result.sort(key=lambda item: (item['nome'] or '').lower())
  return result


def _point_queryset_for_user(request):
  queryset = RegistroPonto.objects.select_related('cartao', 'usuario', 'cartao__usuario').all()
  if user_is_admin_like(request.user):
    return queryset
  return queryset.filter(usuario=request.user)


def _admin_users_queryset():
  return User.objects.filter(groups__name='ic').distinct().order_by('first_name', 'username')


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'home.html'
    login_url = 'login'

    def get(self, request, *args, **kwargs):
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
        return render(request, self.template_name, context)


@csrf_exempt
def receive_sensor_data(request):
    """
    API endpoint to receive sensor data from ESP32 devices.
    Payload must include a 'monitoring' field indicating target (e.g. 'brise' or 'pavimentos').

    For 'brise' monitoring it accepts named keys (ds18b20_1..6, dht11_1_temp/hum, uv_1..2, wind_1..2)
    or the generic sensor1..sensor14 mapping. The function will store readings in the appropriate DB via router.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'}, status=405)

    try:
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON format'}, status=400)

        monitoring = data.get('monitoring', 'default').lower()
        device_id = data.get('device_id')
        if not device_id:
            return JsonResponse({'status': 'error', 'message': 'Missing required field: device_id'}, status=400)

        battery_level = data.get('battery')
        if battery_level is not None:
            try:
                battery_level = float(battery_level)
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': 'Battery must be a number between 0 and 100'}, status=400)
            if not 0 <= battery_level <= 100:
                return JsonResponse({'status': 'error', 'message': 'Battery level must be between 0 and 100'}, status=400)

        # Route to specific model based on monitoring
        if monitoring == 'brise':
            # expected named keys mapping for brise
            expected = ['ds18b20_1','ds18b20_2','ds18b20_3','ds18b20_4','ds18b20_5','ds18b20_6',
                        'dht11_1_temp','dht11_1_hum','dht11_2_temp','dht11_2_hum',
                        'uv_1','uv_2','wind_1','wind_2']
            # accept either named or generic sensor1..sensor14
            if all(k in data for k in [f'sensor{i}' for i in range(1,15)]):
                # generic -> map sensor1..sensor14 to brise fields
                try:
                    vals = [float(data[f'sensor{i}']) for i in range(1,15)]
                except (ValueError, TypeError):
                    return JsonResponse({'status':'error','message':'All sensor values must be numbers'}, status=400)
                brise_kwargs = {
                    'ds18b20_1': vals[0], 'ds18b20_2': vals[1], 'ds18b20_3': vals[2], 'ds18b20_4': vals[3], 'ds18b20_5': vals[4], 'ds18b20_6': vals[5],
                    'dht11_1_temp': vals[6], 'dht11_1_hum': vals[8], 'dht11_2_temp': vals[7], 'dht11_2_hum': vals[9],
                    'uv_1': vals[10], 'uv_2': vals[11], 'wind_1': vals[12], 'wind_2': vals[13]
                }
            else:
                # named
                missing = [k for k in expected if k not in data]
                if missing:
                    return JsonResponse({'status':'error','message':f'Missing fields for brise: {", ".join(missing)}'}, status=400)
                try:
                    brise_kwargs = {k: float(data[k]) for k in expected}
                except (ValueError, TypeError) as e:
                    return JsonResponse({'status':'error','message':'Invalid numeric value in payload'}, status=400)

            brise_kwargs.update({'device_id': device_id, 'battery_level': battery_level})
            reading = BriseSensorReading(**brise_kwargs)
            # Determine which DB alias to use; fall back to default if not configured
            target_db = 'brise' if ('brise' in getattr(django_settings, 'DATABASES', {}) or 'brise' in getattr(settings, 'DATABASES', {})) else 'default'
            try:
                reading.save(using=target_db)
            except ConnectionDoesNotExist:
                # fallback to default if the target alias isn't available at runtime
                reading.save(using='default')
            return JsonResponse({'status':'success','message':'Brise data saved','id': reading.id, 'timestamp': reading.timestamp.isoformat()})

        elif monitoring == 'pavimentos':
            # simple example for pavimentos: expect sensor_a and sensor_b or sensor1/2
            if 'sensor_a' in data and 'sensor_b' in data:
                try:
                    a = float(data['sensor_a'])
                    b = float(data['sensor_b'])
                except (ValueError, TypeError):
                    return JsonResponse({'status':'error','message':'Invalid numeric value for pavimentos'}, status=400)
                reading = PavimentosSensorReading(sensor_a=a, sensor_b=b, device_id=device_id, battery_level=battery_level)
                target_db = 'pavimentos' if ('pavimentos' in getattr(django_settings, 'DATABASES', {}) or 'pavimentos' in getattr(settings, 'DATABASES', {})) else 'default'
                try:
                    reading.save(using=target_db)
                except ConnectionDoesNotExist:
                    reading.save(using='default')
                return JsonResponse({'status':'success','message':'Pavimentos data saved','id': reading.id, 'timestamp': reading.timestamp.isoformat()})
            elif all(k in data for k in ['sensor1','sensor2']):
                try:
                    a = float(data['sensor1'])
                    b = float(data['sensor2'])
                except (ValueError, TypeError):
                    return JsonResponse({'status':'error','message':'Invalid numeric value for pavimentos'}, status=400)
                reading = PavimentosSensorReading(sensor_a=a, sensor_b=b, device_id=device_id, battery_level=battery_level)
                target_db = 'pavimentos' if ('pavimentos' in getattr(django_settings, 'DATABASES', {}) or 'pavimentos' in getattr(settings, 'DATABASES', {})) else 'default'
                try:
                    reading.save(using=target_db)
                except ConnectionDoesNotExist:
                    reading.save(using='default')
                return JsonResponse({'status':'success','message':'Pavimentos data saved','id': reading.id, 'timestamp': reading.timestamp.isoformat()})
            else:
                return JsonResponse({'status':'error','message':'Missing fields for pavimentos'}, status=400)

        else:
            # fallback: store in legacy SensorReading if sensor1..sensor14 are provided
            generic_keys = [f'sensor{i}' for i in range(1, 15)]
            if not all(k in data for k in generic_keys):
                return JsonResponse({'status':'error','message':'Missing generic sensor fields for default storage'}, status=400)
            try:
                sensor_vals = {f'sensor{i}': float(data[f'sensor{i}']) for i in range(1,15)}
            except (ValueError, TypeError):
                return JsonResponse({'status':'error','message':'All sensor values must be numbers'}, status=400)
            reading = SensorReading(timestamp=timezone.now(), device_id=device_id, battery_level=battery_level, **sensor_vals)
            target_db = 'default'
            try:
                reading.save(using=target_db)
            except ConnectionDoesNotExist:
                reading.save(using='default')
            return JsonResponse({'status':'success','message':'Data saved to default sensorreading','id': reading.id, 'timestamp': reading.timestamp.isoformat()})

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error processing sensor data: {str(e)}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'Internal server error'}, status=500)


def custom_error_view(request, exception=None):
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

        context.update({'request_headers': dict(request.headers), 'request_params': QueryDict(request.META.get('QUERY_STRING', '')), 'request_post': request.POST if request.method == 'POST' else None})

    # Determine the status code
    status_code = 500
    if hasattr(exception, 'status_code'):
        status_code = exception.status_code
    context['status_code'] = status_code

    # Log the error
    logger = logging.getLogger(__name__)
    logger.error(f"Error {status_code} at {request.path}\nType: {context['error_type']}\nMessage: {context['error_message']}\nTraceback:\n{''.join(error_traceback)}")

    return render(request, 'error.html', context, status=status_code)


@require_GET
def latest_sensor_data(request):
    latest = SensorReading.objects.order_by('-timestamp').first()
    if not latest:
        return JsonResponse({'error': 'No data available'}, status=404)
    return JsonResponse({'sensor1': latest.sensor1, 'sensor2': latest.sensor2, 'timestamp': latest.timestamp.strftime('%H:%M'), 'battery': latest.battery_level})


@login_required(login_url='login')
def ponto_dashboard(request):
  if not (user_is_ic(request.user) or user_is_admin_like(request.user)):
    return _permission_denied(request)

  queryset = _build_point_filters(request, _point_queryset_for_user(request), allow_admin_filters=user_is_admin_like(request.user)).order_by('-timestamp')
  paginator = Paginator(queryset, 25)
  page_obj = paginator.get_page(request.GET.get('page'))
  registros = list(queryset.order_by('usuario__first_name', 'usuario__username', 'timestamp'))
  totais_por_usuario = _aggregate_totals_by_user(registros)
  registro_mais_recente = queryset.first()

  hoje = timezone.localdate()
  inicio_semana = hoje - timedelta(days=hoje.weekday())
  fim_semana = inicio_semana + timedelta(days=6)
  weekly_queryset = _point_queryset_for_user(request).filter(data_ponto__range=(inicio_semana, fim_semana))
  weekly_seconds = _calculate_worked_seconds(list(weekly_queryset.order_by('timestamp')))

  context = {
    'page_obj': page_obj,
    'totais_por_usuario': totais_por_usuario,
    'registro_mais_recente': registro_mais_recente,
    'weekly_total_hhmm': _format_seconds(weekly_seconds),
    'weekly_total_decimal': round(weekly_seconds / 3600, 2),
    'is_admin_like': user_is_admin_like(request.user),
    'is_ic_user': user_is_ic(request.user),
    'usuarios_ic': _admin_users_queryset() if user_is_admin_like(request.user) else [],
    'filtros': {
      'aluno': request.GET.get('aluno', ''),
      'data': request.GET.get('data', ''),
      'inicio': request.GET.get('inicio', ''),
      'fim': request.GET.get('fim', ''),
      'periodo': request.GET.get('periodo', ''),
    },
  }
  return render(request, 'ponto_dashboard.html', context)


@login_required(login_url='login')
def exportar_relatorio_ponto(request):
  if not user_is_admin_like(request.user):
    return _permission_denied(request)

  queryset = _build_point_filters(request, _point_queryset_for_user(request), allow_admin_filters=True).order_by('usuario__first_name', 'usuario__username', 'timestamp')
  response = HttpResponse(content_type='text/csv')
  response['Content-Disposition'] = 'attachment; filename="relatorio_ponto.csv"'
  writer = csv.writer(response, delimiter=';')
  writer.writerow(['Nome do Aluno', 'UID da Tag', 'Tipo', 'Data', 'Hora', 'Timestamp', 'Observação'])
  for registro in queryset:
    writer.writerow([
      registro.nome_aluno,
      registro.uid_tag,
      registro.tipo_movimento,
      registro.data_ponto.strftime('%d/%m/%Y') if registro.data_ponto else '',
      registro.hora_ponto.strftime('%H:%M:%S') if registro.hora_ponto else '',
      registro.timestamp.strftime('%d/%m/%Y %H:%M:%S') if registro.timestamp else '',
      registro.observacao,
    ])
  return response


@login_required(login_url='login')
def editar_registro_ponto(request, pk):
  if not user_is_admin_like(request.user):
    return _permission_denied(request)

  registro = get_object_or_404(RegistroPonto, pk=pk)

  if request.method == 'POST':
    data_ponto = parse_date(request.POST.get('data_ponto') or '') or registro.data_ponto
    try:
      hora_ponto = datetime.strptime(request.POST.get('hora_ponto'), '%H:%M').time()
    except (TypeError, ValueError):
      hora_ponto = registro.hora_ponto
    tipo_movimento = request.POST.get('tipo_movimento') or registro.tipo_movimento
    registro.data_ponto = data_ponto
    registro.hora_ponto = hora_ponto
    if tipo_movimento in {RegistroPonto.ENTRADA, RegistroPonto.SAIDA}:
      registro.tipo_movimento = tipo_movimento
    registro.observacao = request.POST.get('observacao', registro.observacao)
    registro.timestamp = timezone.make_aware(datetime.combine(data_ponto, hora_ponto), timezone.get_current_timezone())
    registro.save()
    return redirect('ponto_dashboard')

  return render(request, 'editar_ponto.html', {'registro': registro})


@login_required(login_url='login')
def dashboard(request):
    """
    Dashboard view showing charts and summary of last 24 hours
    """
    try:
        # Get data from last 24 hours
        time_threshold = timezone.now() - timedelta(hours=24)
        readings = SensorReading.objects.filter(timestamp__gte=time_threshold).order_by('timestamp')

        # Safely get the last reading (may be None)
        last_reading = readings.last()

        # Compute aggregates once
        agg = readings.aggregate(
            temp_avg=Avg('sensor1'), temp_max=Max('sensor1'), temp_min=Min('sensor1'),
            hum_avg=Avg('sensor7'), hum_max=Max('sensor7'), hum_min=Min('sensor7'),
            batt_avg=Avg('battery_level'), batt_min=Min('battery_level')
        ) if readings.exists() else {}

        # Build summary using safe access
        summary = {
            'temperature': {
                'current': last_reading.sensor1 if last_reading else None,
                'avg': agg.get('temp_avg'),
                'max': agg.get('temp_max'),
                'min': agg.get('temp_min')
            },
            'humidity': {
                'current': last_reading.sensor7 if last_reading else None,
                'avg': agg.get('hum_avg'),
                'max': agg.get('hum_max'),
                'min': agg.get('hum_min')
            },
            'battery': {
                'current': last_reading.battery_level if last_reading else None,
                'avg': agg.get('batt_avg'),
                'min': agg.get('batt_min')
            }
        }

        context = {
            'readings': readings,
            'summary': summary,
            'sensor_names': {1: "Temperatura Externa 1", 2: "Temperatura Externa 2", 3: "Temperatura Solo 1", 4: "Temperatura Solo 2", 5: "Temperatura Ar 1", 6: "Temperatura Ar 2", 7: "Umidade Ar 1", 8: "Umidade Ar 2", 9: "Umidade Solo", 10: "Radiação UV 1", 11: "Radiação UV 2", 12: "Velocidade Vento 1", 13: "Velocidade Vento 2"},
            'units': {1: "°C", 2: "°C", 3: "°C", 4: "°C", 5: "°C", 6: "°C", 7: "%", 8: "%", 9: "%", 10: "UV", 11: "UV", 12: "m/s", 13: "m/s"}
        }
        return render(request, 'dashboard.html', context)

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error in dashboard view: {str(e)}", exc_info=True)
        return render(request, 'error.html', {'error': str(e)})


# Formulário para o Admin cadastrar o cartão e associar ao usuário
class CartaoRFIDForm(forms.ModelForm):
    class Meta:
        model = CartaoRFID
        fields = ['uid', 'usuario']
        widgets = {
            'uid': forms.TextInput(attrs={'class': 'form-control bg-light border-0', 'placeholder': 'Ex: A1 B2 C3 D4'}),
            'usuario': forms.Select(attrs={'class': 'form-select bg-light border-0'}),
        }


@login_required
def ponto_view(request):
    message = None

    if user_is_admin_like(request.user) and request.method == 'POST':
        form = CartaoRFIDForm(request.POST)
        if form.is_valid():
            form.save()
            message = "Cartão vinculado com sucesso!"
            return redirect('cadastrar_cartao')
    else:
        form = CartaoRFIDForm()

    if user_is_admin_like(request.user):
        registros = RegistroPonto.objects.select_related('cartao', 'usuario').all().order_by('-timestamp')
    else:
        registros = RegistroPonto.objects.select_related('cartao', 'usuario').filter(usuario=request.user).order_by('-timestamp')

    context = {
        'form': form,
        'registros': registros,
        'message': message,
    }
    return render(request, 'cadastrar_cartao.html', context)


@csrf_exempt
def registrar_ponto_rfid(request):
    """API endpoint que o ESP8266 vai chamar ao aproximar o cartão"""
    if request.method == 'POST':
        raw_body = request.body.decode('utf-8').strip()
        try:
            payload = json.loads(raw_body) if raw_body.startswith('{') else {}
        except json.JSONDecodeError:
            payload = {}

        raw_uid = payload.get('uid') or payload.get('card_uid') or raw_body
        uid = normalize_rfid_uid(raw_uid)
        if not uid:
            return JsonResponse({"status": "error", "message": "UID do cartão não informado"}, status=400)

        cartao = CartaoRFID.objects.select_related('usuario').filter(uid=uid).first()
        if cartao is None:
            for item in CartaoRFID.objects.select_related('usuario').all():
                if normalize_rfid_uid(item.uid) == uid:
                    cartao = item
                    break
        if cartao is None:
            return JsonResponse({"status": "error", "message": "Cartão não cadastrado"}, status=404)

        now = timezone.localtime(timezone.now())

        with transaction.atomic():
            ultimo_registro = (
                RegistroPonto.objects.select_for_update()
                .filter(cartao=cartao, data_ponto=now.date())
                .order_by('-timestamp')
                .first()
            )
            tipo_movimento = RegistroPonto.ENTRADA if not ultimo_registro or ultimo_registro.tipo_movimento == RegistroPonto.SAIDA else RegistroPonto.SAIDA

            registro = RegistroPonto.objects.create(
                cartao=cartao,
                usuario=cartao.usuario,
                nome_aluno=(cartao.usuario.get_full_name() if cartao.usuario else '') or (cartao.usuario.username if cartao.usuario else 'Aluno sem cadastro'),
                uid_tag=cartao.uid,
                tipo_movimento=tipo_movimento,
                timestamp=now,
                data_ponto=now.date(),
                hora_ponto=now.time().replace(microsecond=0),
            )

        return JsonResponse({
            "status": "success",
            "message": "Ponto registrado com sucesso",
            "tipo_movimento": registro.tipo_movimento,
            "nome_aluno": registro.nome_aluno,
            "uid": registro.uid_tag,
            "data": registro.data_ponto.isoformat(),
            "hora": registro.hora_ponto.strftime('%H:%M:%S'),
            "timestamp": registro.timestamp.isoformat(),
        }, status=200)
    return JsonResponse({"status": "error", "message": "Método inválido"}, status=405)

# Protected selection pages (replace lambdas in urls)
@login_required(login_url='login')
def select_dashboard(request):
    return render(request, 'select_dashboard.html')


@login_required(login_url='login')
def select_table(request):
    return render(request, 'select_table.html')


@login_required(login_url='login')
def dashboard_project(request, project):
    # Exemplo simples, ajuste conforme sua lógica
    return render(request, 'dashboard.html', {'project': project})


@login_required(login_url='login')
def data_table_project(request, project):
    # Exemplo simples, ajuste conforme sua lógica
    return render(request, 'data_table.html', {'project': project})


@login_required(login_url='login')
def data_table(request):
    """
    View showing paginated table with all sensor readings
    """
    try:
        all_readings = SensorReading.objects.all().order_by('-timestamp')
        paginator = Paginator(all_readings, 50)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'page_obj': page_obj,
            'sensor_names': {1: "Temp 1", 2: "Temp 2", 3: "Temp 3", 4: "Temp 4", 5: "Temp 5", 6: "Temp 6", 7: "Hum 1", 8: "Hum 2", 9: "Hum 3", 10: "UV 1", 11: "UV 2", 12: "Vento 1", 13: "Vento 2"},
            'units': {1: "°C", 2: "°C", 3: "°C", 4: "°C", 5: "°C", 6: "°C", 7: "%", 8: "%", 9: "%", 10: "UV", 11: "UV", 12: "m/s", 13: "m/s"}
        }
        return render(request, 'data_table.html', context)

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error in data_table view: {str(e)}", exc_info=True)
        return render(request, 'error.html', {'error': str(e)})


@login_required(login_url='login')
def access_log_list(request):
    logs = AccessLog.objects.select_related('cartao').order_by('-timestamp')
    paginator = Paginator(logs, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'access_log_list.html', {'page_obj': page_obj})


#====== LOGIN FORM ======#
class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)


#====== LOGIN ======#
def login_view(request):
    form = LoginForm(request.POST or None)
    error_message = None
    if request.method == 'POST' and form.is_valid():
        user = authenticate(request, username=form.cleaned_data['username'], password=form.cleaned_data['password'])
        if user is not None:
            if user_is_authorized_for_login(user):
                login(request, user)
                return redirect('home')
            if not user.is_active:
                error_message = 'Seu cadastro ainda não foi autorizado pelo administrador.'
            else:
                error_message = 'Seu usuário não pertence a nenhum grupo ou perfil autorizado.'
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


class RegisterForm(forms.Form):
    username = forms.CharField(label='Usuário', max_length=150)
    password = forms.CharField(label='Senha', widget=forms.PasswordInput)
    first_name = forms.CharField(label='Primeiro Nome', max_length=30)
    last_name = forms.CharField(label='Sobrenome', max_length=30)
    email = forms.EmailField(label='E-mail')
    group = forms.ChoiceField(label='Grupo', choices=[])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # CORREÇÃO: Usa g.name como valor (value) em vez de g.id para bater com a validação do login
        self.fields['group'].choices = [(g.name, g.name) for g in Group.objects.all()]


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
                role_map = {
                    'ic': PerfilUsuario.ROLE_IC,
                    'adm': PerfilUsuario.ROLE_ADMIN,
                    'mestrado': PerfilUsuario.ROLE_SUPERVISOR,
                    'doutorado': PerfilUsuario.ROLE_SUPERVISOR,
                    'professor': PerfilUsuario.ROLE_SUPERVISOR,
                }
                PerfilUsuario.objects.get_or_create(user=user, defaults={'role': role_map.get(group_name, PerfilUsuario.ROLE_IC)})
                message = 'Cadastro realizado! Aguarde o administrador liberar seu acesso.'
    return render(request, 'register.html', {'form': form, 'message': message})
