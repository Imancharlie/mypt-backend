from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.core.urls')),
    path('api/auth/', include('apps.users.urls')),
    path('api/companies/', include('apps.companies.urls')),
    path('api/reports/', include('apps.reports.urls')),
    path('api/ai/', include('apps.ai_assist.urls')),
    path('api/export/', include('apps.exporter.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) 