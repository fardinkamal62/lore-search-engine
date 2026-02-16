from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from backend import views

urlpatterns = [
    path('', views.home_page, name='home_page'),
    path('search/', views.search_page, name='search_page'),
    path('admin/', admin.site.urls),
    path('api/autocomplete', views.auto_complete, name='auto_complete'),
    path('api/search', views.search, name='search'),
]

# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
