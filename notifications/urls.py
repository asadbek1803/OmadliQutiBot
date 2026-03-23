from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # Notification list and management
    path('', views.NotificationListView.as_view(), name='notification_list'),
    path('api/list/', views.api_notifications_list, name='api_notifications_list'),
    path('api/stats/', views.api_notification_stats, name='api_notification_stats'),
    
    # Mark as read
    path('api/<int:notification_id>/read/', views.api_mark_notification_read, name='api_mark_read'),
    path('api/mark-all-read/', views.api_mark_all_notifications_read, name='api_mark_all_read'),
    
    # Preferences
    path('api/preferences/', views.api_notification_preferences, name='api_preferences'),
    path('api/preferences/update/', views.api_update_notification_preferences, name='api_update_preferences'),
    
    # Test notification
    path('api/send-test/', views.api_send_test_notification, name='api_send_test'),
]
