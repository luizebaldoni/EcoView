from django.urls import path
from . import views

urlpatterns = [
    path('api/receive/', views.receive_sensor_data, name= 'receive_sensor_data'),
    path('', views.dashboard, name= 'dashboard'),
    path('table/', views.data_table, name= 'data_table'),
]