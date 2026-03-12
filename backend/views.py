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
    Return phrase suggestions for the authenticated user as they type.

    Suggestions are searchable terms, not file objects — clicking one navigates
    to the search page (/search?q=<phrase>) where matching files are listed.

    Two passes (combined, deduplicated, max 8 results):
      1. Word extraction — split every filename the user owns into individual
         words; keep words that start with the query (case-insensitive).
         These are natural-language words and preferred for display.
      2. Index-term fallback — terms from the user's InvertedIndex that start
         with the query prefix (Porter-stemmed, shown only when pass 1 yields
         fewer than 8 results).
    """
    import re
    query = request.GET.get('q', '').strip().lower()
    user  = _get_user_from_request(request)

    if not user or not query:
        return JsonResponse({'suggestions': [], 'csrf_token': get_token(request)})

    from apps.upload.models import UploadedFile
    from apps.indexer.models import InvertedIndex

    MAX_RESULTS = 8
    seen_phrases: set[str] = set()
    phrases: list[str] = []

    def _add(word: str):
        w = word.lower()
        if w not in seen_phrases and len(w) > 1:
            seen_phrases.add(w)
            phrases.append(w)

    # Pass 1: words extracted from filenames
    filenames = (
        UploadedFile.objects
        .filter(uploaded_by=user, deleted_at=None)
        .values_list('original_filename', flat=True)
    )
    for filename in filenames:
        # strip extension, split on whitespace / underscores / hyphens / dots / brackets
        name = re.sub(r'\.[^.]+$', '', filename)
        for word in re.split(r'[\s_\-.,;:()\[\]{}]+', name):
            if len(word) > 1 and word.lower().startswith(query):
                _add(word)
        if len(phrases) >= MAX_RESULTS:
            break

    # Pass 2: index-term prefix fallback
    if len(phrases) < MAX_RESULTS:
        terms = (
            InvertedIndex.objects
            .filter(
                document__uploaded_by=user,
                document__deleted_at=None,
                term__startswith=query,
            )
            .values_list('term', flat=True)
            .distinct()
            [:MAX_RESULTS]
        )
        for term in terms:
            _add(term)
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
