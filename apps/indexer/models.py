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
    original_term = models.CharField(
        max_length=100,
        default='',
        help_text='Original (lowercased, pre-stem) word for human-readable suggestions.',
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


class DocumentPhrase(models.Model):
    """
    Stores real sentences / phrases extracted from document content at index
    time.  Used by autocomplete to suggest human-readable sentence fragments
    rather than isolated stemmed tokens.

    Each row is one sentence (via NLTK sent_tokenize), cleaned and capped at
    MAX_PHRASE_LENGTH characters.  User isolation follows the same FK chain:
    document → UploadedFile → User.
    """

    MAX_PHRASE_LENGTH = 200

    document = models.ForeignKey(
        'upload.UploadedFile',
        on_delete=models.CASCADE,
        related_name='phrases',
        help_text='The source document this phrase was extracted from.',
    )
    phrase = models.CharField(
        max_length=MAX_PHRASE_LENGTH,
        help_text='A sentence or phrase from the document content.',
    )
    position = models.PositiveIntegerField(
        default=0,
        help_text='Sentence order within the document (0-based).',
    )

    class Meta:
        indexes = [
            models.Index(fields=['phrase']),
            models.Index(fields=['document']),
        ]
        ordering = ['position']

    def __str__(self):
        return f'{self.phrase[:60]}… (doc={self.document_id})'


