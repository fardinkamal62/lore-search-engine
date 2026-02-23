from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from backend import views

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Frontend views
    path('', views.home_page, name='home_page'),
    path('search/', views.search_page, name='search_page'),

    # API endpoints
    path('api/autocomplete', views.auto_complete, name='auto_complete'),
    path('api/search', views.search, name='search'),
    path('api/auth/', include('apps.authentication.urls')),
    path('api/upload/', include('apps.upload.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
