from django.urls import path
from app.views import *

urlpatterns = [
	path('', HomeView.as_view(), name='home'),
    path('api/receive/', receive_sensor_data, name= 'receive_sensor_data'),
    path('dashboard/', dashboard, name= 'dashboard'),
    path('table/', data_table, name= 'data_table'),
	
]