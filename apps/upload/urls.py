from django.urls import path
from . import views

app_name = 'upload'

urlpatterns = [
    path('', views.FileUploadListView.as_view(), name='file_list_upload'),
    path('<int:pk>/', views.FileDetailDeleteView.as_view(), name='file_detail_delete'),
]
