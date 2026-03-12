"""
Indexing pipeline.

`index_document(uploaded_file_id)` is the single entry-point used both by the
upload trigger (background thread) and the `reindex` management command.

TF-IDF strategy — eventual consistency
---------------------------------------
When a new document is indexed, only its own rows are written with TF-IDF
scores computed against the user's corpus *at that moment*.  Existing rows for
other documents in the corpus are NOT updated (eventual consistency).

To recompute accurate TF-IDF scores across the entire corpus run:
    python manage.py reindex --all --user <username>
"""

import logging
import math

from django.db import transaction
from django.db.models import Count

logger = logging.getLogger(__name__)


def index_document(uploaded_file_id: int) -> bool:
    """
    Full indexing pipeline for a single UploadedFile.

    1. Load the UploadedFile; bail out if status is not 'pending' or 'failed'.
    2. Extract text.
    3. Tokenize with positions.
    4. Compute TF per term.
    5. Fetch corpus document_frequency for each term from the user's corpus.
    6. Compute TF-IDF.
    7. Bulk-upsert InvertedIndex rows.
    8. Set status → 'processed'.

    Returns True on success, False on failure.
    """
    # Import here to avoid circular imports at module load time
    from apps.upload.models import UploadedFile
    from apps.indexer.models import InvertedIndex
    from apps.indexer.extractor import extract_text
    from apps.indexer.tokenizer import tokenize_with_positions

    try:
        uploaded_file = UploadedFile.objects.get(pk=uploaded_file_id)
    except UploadedFile.DoesNotExist:
        logger.error('index_document: UploadedFile id=%s not found.', uploaded_file_id)
        return False

    if uploaded_file.status not in ('pending', 'failed'):
        logger.info(
            'index_document: skipping file id=%s (status=%s)',
            uploaded_file_id, uploaded_file.status,
        )
        return False

    logger.info(
        'index_document: starting — id=%s name=%s user=%s',
        uploaded_file_id,
        uploaded_file.original_filename,
        uploaded_file.uploaded_by.username,
    )

    try:
        # ------------------------------------------------------------------ #
        # Step 1: Extract text
        # ------------------------------------------------------------------ #
        raw_text = extract_text(uploaded_file)

        if not raw_text.strip():
            logger.warning(
                'index_document: no text extracted from file id=%s (type=%s) — '
                'marking as processed with 0 terms.',
                uploaded_file_id, uploaded_file.file_type,
            )
            _mark_status(uploaded_file, 'processed')
            return True

        # ------------------------------------------------------------------ #
        # Step 2: Tokenize with positions
        # ------------------------------------------------------------------ #
        term_positions: dict[str, list[int]] = tokenize_with_positions(raw_text)

        if not term_positions:
            logger.warning(
                'index_document: no tokens produced for file id=%s', uploaded_file_id
            )
            _mark_status(uploaded_file, 'processed')
            return True

        total_terms = sum(len(positions) for positions in term_positions.values())

        # ------------------------------------------------------------------ #
        # Step 3: Compute term frequencies
        # ------------------------------------------------------------------ #
        # TF = (occurrences of term in doc) / (total terms in doc)
        term_tf: dict[str, float] = {
            term: len(positions) / total_terms
            for term, positions in term_positions.items()
        }

        # ------------------------------------------------------------------ #
        # Step 4: Fetch corpus document frequencies (user-scoped)
        # ------------------------------------------------------------------ #
        # For each term in this document, count how many of the user's
        # *other* documents (already indexed) contain that term.
        # We add 1 (the current document itself) to get the true DF.
        user = uploaded_file.uploaded_by
        terms = list(term_positions.keys())

        existing_df_qs = (
            InvertedIndex.objects
            .filter(document__uploaded_by=user, term__in=terms)
            .exclude(document_id=uploaded_file_id)
            .values('term')
            .annotate(df=Count('document', distinct=True))
        )
        existing_df: dict[str, int] = {row['term']: row['df'] for row in existing_df_qs}

        # Total number of unique documents the user has indexed so far
        # (excluding the current one being indexed now)
        total_docs = (
            InvertedIndex.objects
            .filter(document__uploaded_by=user)
            .exclude(document_id=uploaded_file_id)
            .values('document')
            .distinct()
            .count()
        ) + 1  # +1 for the current document

        # ------------------------------------------------------------------ #
        # Step 5: Compute TF-IDF and build rows
        # ------------------------------------------------------------------ #
        index_rows = []
        for term, positions in term_positions.items():
            tf = term_tf[term]
            df = existing_df.get(term, 0) + 1   # +1 for the current doc
            idf = math.log((total_docs + 1) / (df + 1)) + 1   # smoothed IDF
            tf_idf = tf * idf

            index_rows.append(
                InvertedIndex(
                    document=uploaded_file,
                    term=term,
                    term_frequency=tf,
                    document_frequency=df,
                    tf_idf=tf_idf,
                    positions=positions,
                )
            )

        # ------------------------------------------------------------------ #
        # Step 6: Bulk upsert within a transaction
        # ------------------------------------------------------------------ #
        with transaction.atomic():
            InvertedIndex.objects.bulk_create(
                index_rows,
                update_conflicts=True,
                unique_fields=['document', 'term'],
                update_fields=['term_frequency', 'document_frequency', 'tf_idf', 'positions'],
            )
            _mark_status(uploaded_file, 'processed')

        logger.info(
            'index_document: completed — id=%s terms=%d',
            uploaded_file_id, len(index_rows),
        )
        return True

    except Exception as exc:
        logger.error(
            'index_document: FAILED for file id=%s: %s',
            uploaded_file_id, exc, exc_info=True,
        )
        try:
            _mark_status(uploaded_file, 'failed')
        except Exception:
            pass
        return False


def reindex_user_corpus(user) -> dict[str, int]:
    """
    Recompute TF-IDF scores for ALL indexed documents belonging to `user`.

    This corrects the eventual-consistency drift that accumulates as new
    documents are added to the corpus.  Intended to be called from the
    `reindex` management command.

    Returns a summary dict: {'reindexed': N, 'failed': M}.
    """
    from apps.upload.models import UploadedFile

    files = UploadedFile.objects.filter(
        uploaded_by=user,
        status='processed',
        deleted_at=None,
    )

    stats = {'reindexed': 0, 'failed': 0}
    for f in files:
        # Reset to pending so index_document doesn't skip it
        f.status = 'pending'
        f.save(update_fields=['status'])

        # Clear existing index entries for a clean rebuild
        from apps.indexer.models import InvertedIndex
        InvertedIndex.objects.filter(document=f).delete()

        ok = index_document(f.pk)
        if ok:
            stats['reindexed'] += 1
        else:
            stats['failed'] += 1

    return stats


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _mark_status(uploaded_file, status: str):
    uploaded_file.status = status
    uploaded_file.save(update_fields=['status', 'updated_at'])

