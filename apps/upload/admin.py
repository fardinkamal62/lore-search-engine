from django.contrib import admin
from .models import UploadedFile


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'file_type', 'file_size', 'uploaded_by', 'status', 'uploaded_at')
    list_filter = ('file_type', 'status', 'uploaded_at')
    search_fields = ('original_filename', 'uploaded_by__username')
    readonly_fields = ('uploaded_at', 'updated_at', 'file_size', 'file_type', 'original_filename')

