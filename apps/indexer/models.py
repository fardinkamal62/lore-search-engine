from django.db import models
from django.conf import settings


class InvertedIndex(models.Model):
    """
    Single-table inverted index storing one row per (document, term) pair.

    User isolation is enforced implicitly: every query must filter through
    document__uploaded_by=<user>, following the FK chain from this table
    → UploadedFile → User.

    TF-IDF is computed at index time for the new document only (eventual
    consistency). Run `manage.py reindex --all` to recompute the full corpus
    scores after many documents have been indexed.
    """

    document = models.ForeignKey(
        'upload.UploadedFile',
        on_delete=models.CASCADE,
        related_name='index_entries',
        help_text='The source document this term was extracted from.',
    )
    term = models.CharField(
        max_length=100,
        db_index=True,
        help_text='Normalized (lowercased, stemmed) token.',
    )
    term_frequency = models.FloatField(
        help_text='TF = occurrences of this term / total terms in the document.',
    )
    document_frequency = models.IntegerField(
        default=1,
        help_text='Number of documents in the owning user\'s corpus that contain this term.',
    )
    tf_idf = models.FloatField(
        help_text='Precomputed TF-IDF score at index time.',
    )
    positions = models.JSONField(
        default=list,
        help_text='List of token-offset positions (0-based) of this term in the document.',
    )
    indexed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('document', 'term')]
        indexes = [
            models.Index(fields=['term']),
            models.Index(fields=['document']),
        ]
        ordering = ['-tf_idf']

    def __str__(self):
        return f'"{self.term}" in {self.document.original_filename}'

