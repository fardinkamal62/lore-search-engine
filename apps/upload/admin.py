from django.contrib import admin
from .models import UploadedFile


def reindex_selected_files(modeladmin, request, queryset):
    """Admin action — clears index entries for the selected files and re-indexes them."""
    from apps.indexer.models import InvertedIndex, DocumentPhrase
    from apps.indexer.pipeline import index_document

    ok = failed = 0
    for f in queryset:
        # Reset status and clear old entries for a clean rebuild
        f.status = 'pending'
        f.save(update_fields=['status'])
        InvertedIndex.objects.filter(document=f).delete()
        DocumentPhrase.objects.filter(document=f).delete()

        if index_document(f.pk):
            ok += 1
        else:
            failed += 1

    modeladmin.message_user(
        request,
        f'{ok} file(s) reindexed successfully, {failed} failed.',
    )


reindex_selected_files.short_description = 'Reindex selected files'


def reindex_all_user_files(modeladmin, request, queryset):
    """Admin action — reindex ALL files for each user represented in the selection."""
    from apps.indexer.pipeline import reindex_user_corpus

    users = set(queryset.values_list('uploaded_by', flat=True))
    from django.contrib.auth import get_user_model
    User = get_user_model()

    total_ok = total_fail = 0
    for user_id in users:
        user = User.objects.get(pk=user_id)
        stats = reindex_user_corpus(user)
        total_ok += stats['reindexed']
        total_fail += stats['failed']

    modeladmin.message_user(
        request,
        f'Full reindex complete: {total_ok} reindexed, {total_fail} failed '
        f'across {len(users)} user(s).',
    )


reindex_all_user_files.short_description = 'Reindex ALL files for selected user(s)'


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'file_type', 'file_size', 'uploaded_by', 'status', 'uploaded_at')
    list_filter = ('file_type', 'status', 'uploaded_at')
    search_fields = ('original_filename', 'uploaded_by__username')
    readonly_fields = ('uploaded_at', 'updated_at', 'file_size', 'file_type', 'original_filename')
    actions = [reindex_selected_files, reindex_all_user_files]

