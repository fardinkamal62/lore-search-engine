from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from rest_framework.authtoken.models import Token
import time
import json


def home_page(request):
    """Simple home page view"""
    context = {'timestamp': int(time.time())}
    response = render(request, 'home_page.html', context)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


def login_page(request):
    """Login page view"""
    context = {'timestamp': int(time.time())}
    response = render(request, 'login_page.html', context)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


def search_page(request):
    """Search results page view"""
    query = request.GET.get('q', '')
    context = {'timestamp': int(time.time()), 'query': query}
    response = render(request, 'search_page.html', context)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


def profile_page(request):
    """Profile page — shows the authenticated user's uploaded files."""
    context = {'timestamp': int(time.time())}
    response = render(request, 'profile_page.html', context)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


@ensure_csrf_cookie
def auto_complete(request):
    """
    Return prefix autocomplete phrase suggestions for the authenticated user.

    Suggestions are built by a Trie over user filenames and indexed content
    phrases. Response shape remains: {'suggestions': [{'phrase': ...}], ...}.
    """
    import re

    query = request.GET.get('q', '').strip().lower()
    user  = _get_user_from_request(request)

    if not user or not query:
        return JsonResponse({'suggestions': [], 'csrf_token': get_token(request)})

    from apps.upload.models import UploadedFile
    from apps.indexer.models import DocumentPhrase

    MAX_RESULTS      = 8
    MAX_PHRASE_WORDS  = 7
    SHORT_WINDOW      = 4

    seen:    set[str]  = set()
    phrases: list[str] = []

    def _add(phrase: str) -> bool:
        key = phrase.lower().strip()
        if key and key not in seen and len(key) > 1:
            seen.add(key)
            phrases.append(phrase.strip())
            return True
        return False

    def _clean_filename(filename: str) -> str:
        name = re.sub(r'\.[^.]+$', '', filename)
        name = re.sub(r'[\s_\-]+', ' ', name)
        name = re.sub(r'[()[\]{}]', ' ', name)
        return re.sub(r'\s{2,}', ' ', name).strip()

    # ── Pass 1: filename-based phrases ────────────────────────────────────
    filenames = list(
        UploadedFile.objects
        .filter(uploaded_by=user, deleted_at=None)
        .values_list('original_filename', flat=True)
    )

    for filename in filenames:
        cleaned = _clean_filename(filename)
        words   = cleaned.split()
        for i, word in enumerate(words):
            if word.lower().startswith(query):
                full = ' '.join(words[:MAX_PHRASE_WORDS])
                if len(words) > MAX_PHRASE_WORDS:
                    full += '…'
                _add(full)
                start  = max(0, i - 1)
                end    = min(len(words), i + SHORT_WINDOW)
                window = ' '.join(words[start:end])
                if window.lower() != full.lower():
                    _add(window)
                break
        if len(phrases) >= MAX_RESULTS:
            break

    # ── Pass 2: content phrases — real sentences from DocumentPhrase ──────
    if len(phrases) < MAX_RESULTS:
        remaining = MAX_RESULTS - len(phrases)
        content_phrases = (
            DocumentPhrase.objects
            .filter(
                document__uploaded_by=user,
                document__deleted_at=None,
                phrase__icontains=query,
            )
            .values_list('phrase', flat=True)
            [:remaining * 3]    # fetch extra to account for dedup
        )
        for raw_phrase in content_phrases:
            _add(raw_phrase)
            if len(phrases) >= MAX_RESULTS:
                break

    suggestions = [{'phrase': p} for p in phrases[:MAX_RESULTS]]
    return JsonResponse({'suggestions': suggestions, 'csrf_token': get_token(request)})


def _get_user_from_request(request):
    """
    Resolve the authenticated user from a DRF Token in the Authorization header.
    Returns the User instance, or None if the token is missing / invalid.
    """
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Token '):
        return None
    key = auth_header.split(' ', 1)[1].strip()
    try:
        token = Token.objects.select_related('user').get(key=key)
        return token.user
    except Token.DoesNotExist:
        return None


@ensure_csrf_cookie
@require_http_methods(["POST"])
def search(request):
    """
    Search the authenticated user's indexed documents.

    Returns results ranked by TF-IDF score. Each result contains the file id,
    filename, file type, relevance score, and the matched terms.
    Returns an empty results list (with a human-readable message) when nothing
    matches or no files have been uploaded yet.
    """
    user = _get_user_from_request(request)
    if user is None:
        return JsonResponse({"error": "Authentication required."}, status=401)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    query = data.get('query', '').strip()
    if not query:
        return JsonResponse({"error": "Query must not be empty."}, status=400)

    from apps.indexer.services import IndexerService
    results = IndexerService.search(user, query, request=request)

    if not results:
        return JsonResponse({
            "csrf_token": get_token(request),
            "results": [],
            "message": "No matching documents found.",
            "count": 0,
        })

    return JsonResponse({
        "csrf_token": get_token(request),
        "results": results,
        "count": len(results),
    })
