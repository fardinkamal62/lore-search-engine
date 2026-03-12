"""
Tokenizer module.

Converts raw text into a cleaned, stemmed list of tokens suitable for
building an inverted index.

Pipeline:
  1. Lowercase
  2. NLTK word_tokenize (handles punctuation and contractions)
  3. Keep only alphabetic tokens (drop numbers, punctuation)
  4. Remove English stop-words (NLTK corpus)
  5. Porter-stem each token
"""

import logging
import re

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# NLTK lazy-load helpers (downloads are done at startup via Dockerfile /
# management command, but we guard here in case they haven't run yet).
# ---------------------------------------------------------------------------

_stopwords = None
_stemmer = None


def _get_stopwords():
    global _stopwords
    if _stopwords is None:
        try:
            from nltk.corpus import stopwords as sw
            _stopwords = set(sw.words('english'))
        except LookupError:
            import nltk
            nltk.download('stopwords', quiet=True)
            from nltk.corpus import stopwords as sw
            _stopwords = set(sw.words('english'))
    return _stopwords


def _get_stemmer():
    global _stemmer
    if _stemmer is None:
        from nltk.stem import PorterStemmer
        _stemmer = PorterStemmer()
    return _stemmer


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def tokenize(text: str) -> list[str]:
    """
    Convert raw text into a list of cleaned, stemmed tokens.

    Returns an empty list for empty / None input.
    """
    if not text:
        return []

    try:
        return _tokenize(text)
    except Exception as exc:
        logger.error('Tokenization failed: %s', exc, exc_info=True)
        # Fallback: very simple whitespace split
        return _simple_tokenize(text)


def tokenize_with_positions(text: str) -> dict[str, dict]:
    """
    Tokenize text and record the 0-based token-offset position of every
    occurrence of each stemmed term, plus the most common original (pre-stem)
    word form.

    Returns:
        {
            'stemmed_term': {
                'positions': [pos0, pos5, pos12, ...],
                'original':  'most_common_prestem_form',
            },
            ...
        }
    """
    if not text:
        return {}

    try:
        return _tokenize_with_positions(text)
    except Exception as exc:
        logger.error('Position-aware tokenization failed: %s', exc, exc_info=True)
        # Fallback: positional map from simple tokenization
        tokens = _simple_tokenize(text)
        result: dict[str, dict] = {}
        for pos, token in enumerate(tokens):
            if token not in result:
                result[token] = {'positions': [], 'original': token}
            result[token]['positions'].append(pos)
        return result


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

_ALPHA_RE = re.compile(r'^[a-z]+$')


def _tokenize(text: str) -> list[str]:
    try:
        from nltk.tokenize import word_tokenize
        raw_tokens = word_tokenize(text.lower())
    except LookupError:
        import nltk
        nltk.download('punkt_tab', quiet=True)
        from nltk.tokenize import word_tokenize
        raw_tokens = word_tokenize(text.lower())

    stop_words = _get_stopwords()
    stemmer = _get_stemmer()

    result = []
    for tok in raw_tokens:
        if not _ALPHA_RE.match(tok):
            continue
        if tok in stop_words:
            continue
        result.append(stemmer.stem(tok))
    return result


def _tokenize_with_positions(text: str) -> dict[str, dict]:
    try:
        from nltk.tokenize import word_tokenize
        raw_tokens = word_tokenize(text.lower())
    except LookupError:
        import nltk
        nltk.download('punkt_tab', quiet=True)
        from nltk.tokenize import word_tokenize
        raw_tokens = word_tokenize(text.lower())

    stop_words = _get_stopwords()
    stemmer = _get_stemmer()

    result: dict[str, dict] = {}
    original_counts: dict[str, dict[str, int]] = {}   # stemmed → {original → count}
    offset = 0
    for tok in raw_tokens:
        if not _ALPHA_RE.match(tok):
            continue
        if tok in stop_words:
            continue
        stemmed = stemmer.stem(tok)
        if stemmed not in result:
            result[stemmed] = {'positions': [], 'original': tok}
            original_counts[stemmed] = {}
        result[stemmed]['positions'].append(offset)
        original_counts[stemmed][tok] = original_counts[stemmed].get(tok, 0) + 1
        offset += 1

    # Pick the most frequent original form for each stem
    for stemmed, counts in original_counts.items():
        best = max(counts, key=counts.get)
        result[stemmed]['original'] = best

    return result


def _simple_tokenize(text: str) -> list[str]:
    """Minimal fallback tokenizer that doesn't depend on NLTK."""
    return [w for w in text.lower().split() if _ALPHA_RE.match(w)]

