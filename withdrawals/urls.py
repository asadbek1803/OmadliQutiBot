from django.urls import path
from . import views

app_name = 'withdrawals'

urlpatterns = [
    path('screenshots/<str:filename>', views.serve_withdrawal_screenshot, name='serve_screenshot'),
    path('api/screenshots/', views.serve_withdrawal_screenshots_list, name='screenshots_list'),
]
