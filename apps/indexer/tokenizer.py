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


def tokenize_with_positions(text: str) -> dict[str, list[int]]:
    """
    Tokenize text and record the 0-based token-offset position of every
    occurrence of each stemmed term.

    Returns:
        {
            'term': [pos0, pos5, pos12, ...],
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
        positions: dict[str, list[int]] = {}
        for pos, token in enumerate(tokens):
            positions.setdefault(token, []).append(pos)
        return positions


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


def _tokenize_with_positions(text: str) -> dict[str, list[int]]:
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

    positions: dict[str, list[int]] = {}
    offset = 0
    for tok in raw_tokens:
        if not _ALPHA_RE.match(tok):
            continue
        if tok in stop_words:
            continue
        stemmed = stemmer.stem(tok)
        positions.setdefault(stemmed, []).append(offset)
        offset += 1
    return positions


def _simple_tokenize(text: str) -> list[str]:
    """Minimal fallback tokenizer that doesn't depend on NLTK."""
    return [w for w in text.lower().split() if _ALPHA_RE.match(w)]

