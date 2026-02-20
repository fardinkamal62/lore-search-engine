from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
import time
import json


def home_page(request):
    """Simple home page view"""
    """ Render from static/home_page.html """
    context = {
        'timestamp': int(time.time())
    }
    response = render(request, 'home_page.html', context)
    # Add cache control headers for development
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


def search_page(request):
    """Search results page view"""
    query = request.GET.get('q', '')
    context = {
        'timestamp': int(time.time()),
        'query': query
    }
    response = render(request, 'search_page.html', context)
    # Add cache control headers for development
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


@ensure_csrf_cookie
def auto_complete(request):
    """
    Return a JSON response with auto-complete suggestions based on the query parameter.
    :param request: The HTTP request object containing the query parameter 'q'.
    """
    query = request.GET.get('q', '')
    # Here you would implement your logic to generate suggestions based on the query.
    # For demonstration purposes, we'll return a static list of suggestions.
    suggestions = [
        {"title": "Suggestion 1 for " + query, "url": "/suggestion1"},
        {"title": "Suggestion 2 for " + query, "url": "/suggestion2"},
        {"title": "Suggestion 3 for " + query, "url": "/suggestion3"},
    ]
    return JsonResponse({
        "suggestions": suggestions,
        "csrf_token": get_token(request),
    })


@ensure_csrf_cookie
@require_http_methods(["POST"])
def search(request):
    """
    Return a JSON response with search results based on the query in POST body.
    :param request: The HTTP request object containing the query in POST body.
    """
    try:
        data = json.loads(request.body)
        query = data.get('query', '')
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # Here you would implement your logic to perform a search based on the query.
    # For demonstration purposes, we'll return a static list of search results.
    results = [
        {
            "title": "Search result for " + query,
            "resource-name": "Example Site 1",
            "favicon": "https://www.example.com/favicon.ico",
            "description": "Description for search result 1",
            "url": "https://www.example.com/search1",
            "category": ["pdf"]
        },
        {
            "title": "Another search result for " + query,
            "resource-name": "Example Site 2",
            "favicon": "https://www.example.com/favicon.ico",
            "description": "Description for search result 2",
            "url": "https://www.example.com/search2",
            "category": ["video"]
        },
        {
            "title": "Yet another search result for " + query,
            "resource-name": "Example Site 3",
            "favicon": "https://www.example.com/favicon.ico",
            "description": "Description for search result 3",
            "url": "https://www.example.com/search3",
            "category": ["article"]
        }
    ]
    return JsonResponse({
        "csrf_token": get_token(request),
        "results": results
    })
