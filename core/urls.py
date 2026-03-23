from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('bot/', include('bot.urls')),
    path('webapp/', include('webapp.urls')),
    path('rewards/', include('rewards.urls')),
    path('withdrawals/', include('withdrawals.urls')),
    path('notifications/', include('notifications.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
