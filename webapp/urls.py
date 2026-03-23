from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='webapp_dashboard'),
    path('api/init/', views.api_init_data, name='api_init_data'),
    path('api/spin/', views.api_spin, name='api_spin'),
    path('api/wallet/', views.api_wallet, name='api_wallet'),
    path('api/withdraw/', views.api_withdraw, name='api_withdraw'),
    path('api/leaders/', views.api_leaders, name='api_leaders'),
    path('api/tasks/list/', views.api_tasks_list, name='api_tasks_list'),
    path('api/tasks/verify/', views.api_tasks_verify, name='api_tasks_verify'),
]
