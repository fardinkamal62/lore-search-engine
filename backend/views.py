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
    Return autocomplete suggestions for the authenticated user.

    Two passes (combined, deduplicated, max 8 results):
      1. Filename match  — UploadedFile.original_filename icontains query
      2. Content match   — InvertedIndex terms that start with the tokenized query,
                           pulling the parent document (processed files only)

    Each suggestion carries { title, file_url, file_type } so the frontend
    can open the file directly without a round-trip to the search page.
    """
    query = request.GET.get('q', '').strip()
    user  = _get_user_from_request(request)

    if not user or not query:
        return JsonResponse({'suggestions': [], 'csrf_token': get_token(request)})

    from apps.upload.models import UploadedFile
    from apps.indexer.models import InvertedIndex
    from apps.indexer.tokenizer import tokenize

    MAX_RESULTS = 8
    seen_ids    = set()
    suggestions = []

    def _to_suggestion(f):
        return {
            'title':     f.original_filename,
            'file_url':  request.build_absolute_uri(f.file.url),
            'file_type': f.file_type,
        }

    # Pass 1: filename contains query (all statuses except deleted)
    filename_qs = (
        UploadedFile.objects
        .filter(uploaded_by=user, deleted_at=None, original_filename__icontains=query)
        .order_by('-uploaded_at')[:MAX_RESULTS]
    )
    for f in filename_qs:
        seen_ids.add(f.pk)
        suggestions.append(_to_suggestion(f))

    # Pass 2: indexed-term prefix match (only processed files)
    if len(suggestions) < MAX_RESULTS:
        query_terms = tokenize(query)
        if query_terms:
            remaining = MAX_RESULTS - len(suggestions)
            term_docs = (
                InvertedIndex.objects
                .filter(
                    document__uploaded_by=user,
                    document__deleted_at=None,
                    document__status='processed',
                    term__in=query_terms,
                )
                .exclude(document__pk__in=seen_ids)
                .select_related('document')
                .order_by('-tf_idf')[:remaining * 3]   # fetch extra, dedupe below
            )
            for entry in term_docs:
                doc = entry.document
                if doc.pk not in seen_ids:
                    seen_ids.add(doc.pk)
                    suggestions.append(_to_suggestion(doc))
                if len(suggestions) >= MAX_RESULTS:
                    break

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
