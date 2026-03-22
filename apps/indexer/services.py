"""
IndexerService — user-scoped query helpers for the InvertedIndex table.

All methods enforce user isolation by filtering through
document__uploaded_by=user, so no cross-user data can leak.
"""

import logging
import re

from .models import InvertedIndex
from .trie import PrefixTrie

logger = logging.getLogger(__name__)


_WS_RE = re.compile(r'\s+')


class IndexerService:

    @staticmethod
    def search(user, query: str, limit: int = 20, request=None) -> list[dict]:
        """
        Search the user's corpus for the given query string.

        Returns a ranked list of dicts:
            [
                {
                    'file_id':          <int>,
                    'original_filename':<str>,
                    'file_type':        <str>,
                    'score':            <float>,   # sum of TF-IDF across matched terms
                    'matched_phrases':  [<str>, ...],  # sentences containing the query
                },
                ...
            ]

        Ranking: sum of TF-IDF scores for each matched term per document,
        sorted descending.
        """
        from apps.indexer.tokenizer import tokenize
        from apps.indexer.models import DocumentPhrase

        if not query.strip():
            return []

        query_terms = list(set(tokenize(query)))
        if not query_terms:
            return []

        # Fetch matching index entries for user's corpus
        entries = (
            InvertedIndex.objects
            .filter(document__uploaded_by=user, term__in=query_terms)
            .select_related('document')
        )

        # Aggregate scores per document
        doc_scores: dict[int, dict] = {}
        for entry in entries:
            doc = entry.document
            if doc.deleted_at is not None:
                continue  # skip soft-deleted files
            if doc.pk not in doc_scores:
                if request is not None:
                    file_url = request.build_absolute_uri(doc.file.url)
                else:
                    file_url = doc.file.url
                doc_scores[doc.pk] = {
                    'file_id': doc.pk,
                    'original_filename': doc.original_filename,
                    'file_type': doc.file_type,
                    'file_url': file_url,
                    'score': 0.0,
                    'matched_phrases': set(),
                }
            doc_scores[doc.pk]['score'] += entry.tf_idf

        # For each document, fetch matching phrases
        for doc_id in doc_scores.keys():
            phrases = DocumentPhrase.objects.filter(
                document_id=doc_id,
                phrase__icontains=query
            ).values_list('phrase', flat=True)[:5]  # limit to 5 phrases per doc
            doc_scores[doc_id]['matched_phrases'] = list(phrases)

        # Convert sets to lists for JSON serialization
        for doc_data in doc_scores.values():
            if not doc_data['matched_phrases']:
                # Fallback: show filename-based phrase if no content phrases
                doc_data['matched_phrases'] = [doc_data['original_filename']]

        # Sort by score descending
        results = sorted(doc_scores.values(), key=lambda x: x['score'], reverse=True)
        return results[:limit]

    @staticmethod
    def get_document_index(user, file_id: int) -> list[InvertedIndex]:
        """
        Return all index entries for a single document owned by user.
        Raises PermissionError if the file doesn't belong to the user.
        """
        entries = InvertedIndex.objects.filter(
            document_id=file_id,
            document__uploaded_by=user,
        ).order_by('-tf_idf')

        return list(entries)

    @staticmethod
    def get_index_stats(user) -> dict:
        """
        Return summary statistics for the user's index corpus.
        """
        from django.db.models import Count

        stats = InvertedIndex.objects.filter(
            document__uploaded_by=user
        ).aggregate(
            total_entries=Count('id'),
            unique_terms=Count('term', distinct=True),
            indexed_documents=Count('document', distinct=True),
        )
        return stats

    @staticmethod
    def delete_document_index(user, file_id: int) -> int:
        """
        Delete all index entries for a document owned by user.
        Returns the number of deleted rows.
        """
        deleted_count, _ = InvertedIndex.objects.filter(
            document_id=file_id,
            document__uploaded_by=user,
        ).delete()
        return deleted_count


class AutocompleteService:
    """Prefix autocomplete built on top of an in-memory Trie."""

    MAX_FILENAME_WORDS = 7
    MAX_CONTENT_PHRASES = 2500

    @staticmethod
    def get_suggestions(user, query: str, limit: int = 8) -> list[str]:
        normalized_query = AutocompleteService._normalize_query(query)
        if not user or not normalized_query:
            return []

        trie = AutocompleteService._build_user_trie(user)
        return trie.suggest(normalized_query, limit=limit)

    @staticmethod
    def _normalize_query(query: str) -> str:
        return _WS_RE.sub(' ', (query or '').strip().lower())

    @staticmethod
    def _clean_filename(filename: str) -> str:
        name = re.sub(r'\.[^.]+$', '', filename or '')
        name = re.sub(r'[\s_\-]+', ' ', name)
        name = re.sub(r'[()[\]{}]', ' ', name)
        return _WS_RE.sub(' ', name).strip()

    @staticmethod
    def _filename_phrases(filename: str) -> list[str]:
        cleaned = AutocompleteService._clean_filename(filename)
        if not cleaned:
            return []

        words = cleaned.split()
        if not words:
            return []

        phrases: list[str] = []
        max_words = AutocompleteService.MAX_FILENAME_WORDS

        full = ' '.join(words[:max_words])
        if len(words) > max_words:
            full += '...'
        phrases.append(full)

        for i in range(1, len(words)):
            window = ' '.join(words[i:i + max_words])
            if window:
                phrases.append(window)

        # Preserve order while deduplicating.
        return list(dict.fromkeys(phrases))

    @staticmethod
    def _build_user_trie(user) -> PrefixTrie:
        from apps.indexer.models import DocumentPhrase
        from apps.upload.models import UploadedFile

        trie = PrefixTrie(max_node_suggestions=32)

        files = UploadedFile.objects.filter(
            uploaded_by=user,
            deleted_at=None,
        ).order_by('-uploaded_at').values_list('original_filename', flat=True)

        for rank, filename in enumerate(files):
            weight = 3.0 - (rank * 0.001)
            for phrase in AutocompleteService._filename_phrases(filename):
                trie.insert(phrase, weight=weight)

        content_phrases = (
            DocumentPhrase.objects
            .filter(document__uploaded_by=user, document__deleted_at=None)
            .order_by('-document__uploaded_at', 'position')
            .values_list('phrase', flat=True)[:AutocompleteService.MAX_CONTENT_PHRASES]
        )
        for rank, phrase in enumerate(content_phrases):
            weight = 2.0 - (rank * 0.0005)
            trie.insert(phrase, weight=weight)

        return trie


