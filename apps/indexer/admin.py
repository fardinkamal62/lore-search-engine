from django.contrib import admin

from .models import InvertedIndex, DocumentPhrase


@admin.register(InvertedIndex)
class InvertedIndexAdmin(admin.ModelAdmin):
    list_display = ('term', 'original_term', 'document', 'term_frequency', 'document_frequency', 'tf_idf', 'indexed_at')
    list_filter = ('document__file_type',)
    search_fields = ('term', 'original_term', 'document__original_filename', 'document__uploaded_by__username')
    readonly_fields = ('indexed_at',)
    ordering = ('-tf_idf',)


@admin.register(DocumentPhrase)
class DocumentPhraseAdmin(admin.ModelAdmin):
    list_display = ('phrase_preview', 'document', 'position')
    list_filter = ('document__file_type',)
    search_fields = ('phrase', 'document__original_filename', 'document__uploaded_by__username')
    ordering = ('document', 'position')

    @admin.display(description='Phrase')
    def phrase_preview(self, obj):
        return obj.phrase[:80] + '…' if len(obj.phrase) > 80 else obj.phrase


