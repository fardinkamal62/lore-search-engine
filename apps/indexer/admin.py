from django.contrib import admin

from .models import InvertedIndex


@admin.register(InvertedIndex)
class InvertedIndexAdmin(admin.ModelAdmin):
    list_display = ('term', 'document', 'term_frequency', 'document_frequency', 'tf_idf', 'indexed_at')
    list_filter = ('document__file_type',)
    search_fields = ('term', 'document__original_filename', 'document__uploaded_by__username')
    readonly_fields = ('indexed_at',)
    ordering = ('-tf_idf',)

