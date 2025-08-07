from django.urls import path
from app.views import *

urlpatterns = [
	path('', HomeView.as_view(), name='home'),
    path('api/receive/', receive_sensor_data, name= 'receive_sensor_data'),
    path('dashboard/', dashboard, name= 'dashboard'),
    path('table/', data_table, name= 'data_table'),
    path('api/latest/', latest_sensor_data, name='latest_sensor_data'),
    path('dashboards/', lambda request: render(request, 'select_dashboard.html'), name='select_dashboard'),
    path('dashboard/<str:project>/', dashboard_project, name='dashboard_project'),
    path('tables/', lambda request: render(request, 'select_table.html'), name='select_table'),
    path('table/<str:project>/', data_table_project, name='data_table_project'),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
	path('logout/', logout_view, name='logout'),
]