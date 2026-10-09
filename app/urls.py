from django.urls import path
from django.shortcuts import render
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('api/receive/', views.receive_sensor_data, name='receive_sensor_data'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('table/', views.data_table, name='data_table'),
    path('api/latest/', views.latest_sensor_data, name='latest_sensor_data'),
    path('dashboards/', views.select_dashboard, name='select_dashboard'),
    path('dashboard/<str:project>/', views.dashboard_project, name='dashboard_project'),
    path('tables/', views.select_table, name='select_table'),
    path('table/<str:project>/', views.data_table_project, name='data_table_project'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('api/verifica_cartao/', views.verifica_cartao, name='verifica_cartao'),
    path('api/ponto/', views.registrar_ponto_rfid, name='registrar_ponto_rfid'), # Rota do ESP8266
    path('acessos/', views.access_log_list, name='access_log_list'),
    path('cartoes/cadastrar/', views.ponto_view, name='cadastrar_cartao'),     # Alterado de cadastrar_cartao para ponto_view
]