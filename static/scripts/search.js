// Auth guard — redirect to /login/ if no token
const AUTH_TOKEN = localStorage.getItem('auth_token');
if (!AUTH_TOKEN) {
    window.location.replace('/login/?next=' + encodeURIComponent(window.location.pathname + window.location.search));
}

const DEBOUNCE_MS = 250;
let debounceTimer = null;

// jQuery-wrapped DOM refs
const $input = $('#search-input');
const $results = $('#search-results');
const $button = $('#search');
const $autoSuggestionResults = $('#autosuggestion-results');

function showLoading() {
    $results.html('<div class="text-center my-5"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>');
}

function showMessage(text) {
    $results.html('<div class="text-muted text-center mt-5">' + text + '</div>');
}

function showError(text) {
    $results.html('<div class="alert alert-danger">' + text + '</div>');
}

function showAutoSuggestionLoading() {
    $autoSuggestionResults.html('<div class="text-center my-3"><div class="spinner-border spinner-border-sm" role="status"><span class="visually-hidden">Loading...</span></div></div>');
}

function showAutoSuggestionMessage(text) {
    $autoSuggestionResults.html('<div class="text-muted text-center mt-2">' + text + '</div>');
}

function showAutoSuggestionError(text) {
    $autoSuggestionResults.html('<div class="alert alert-danger">' + text + '</div>');
}

function renderAutoSuggestionResults(result) {
    if (!result || !Array.isArray(result.suggestions) || result.suggestions.length === 0) {
        $autoSuggestionResults.empty().addClass('d-none');
        return;
    }

    const $container = $('<div>').addClass('list-group w-100');

    result.suggestions.forEach(item => {
        const $a = $('<a>')
            .addClass('list-group-item list-group-item-action d-flex align-items-center gap-2')
            .attr('href', item.file_url || '#')
            .attr('target', '_blank')
            .attr('rel', 'noopener noreferrer');

        const $name = $('<span>').addClass('flex-grow-1 text-truncate').text(item.title || 'Untitled');
        const $badge = $('<span>')
            .addClass('badge bg-secondary flex-shrink-0')
            .text((item.file_type || '').toUpperCase());

        $a.append($name, $badge);
        $container.append($a);
    });

    $autoSuggestionResults.removeClass('d-none').empty().append($container);
}

function logout() {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    window.location.replace('/login/');
}

function renderSearchResults(result) {
    if (!result || !Array.isArray(result.results) || result.results.length === 0) {
        showMessage(result?.message || 'No results found.');
        return;
    }

    const $container = $('<div>').addClass('list-group w-100');

    result.results.forEach(item => {
        const $item = $('<div>').addClass('list-group-item');

        // Filename as a link that opens in a new tab
        const $title = $('<a>')
            .addClass('result-title d-block')
            .attr('href', item.file_url || '#')
            .attr('target', '_blank')
            .attr('rel', 'noopener noreferrer')
            .text(item.original_filename || 'Untitled');

        // File type badge only (no score)
        const $meta = $('<div>').addClass('result-meta d-flex align-items-center');
        const $type = $('<span>').addClass('result-category').text(item.file_type || '');
        $meta.append($type);

        // Matched terms
        const $terms = $('<div>').addClass('mt-2');
        if (item.matched_terms && item.matched_terms.length) {
            item.matched_terms.forEach(term => {
                $terms.append($('<span>').addClass('result-category me-1').text(term));
            });
        }

        $item.append($title, $meta, $terms);
        $container.append($item);
    });

    $results.empty().append($container);
}

async function handleSearchQuery(query) {
    if (!query) {
        $autoSuggestionResults.empty().addClass('d-none');
        return;
    }

    $autoSuggestionResults.removeClass('d-none');
    showAutoSuggestionLoading();
    try {
        const response = await fetch(`/api/autocomplete?q=${encodeURIComponent(query)}`, {
            headers: { 'Authorization': 'Token ' + AUTH_TOKEN },
        });
        if (response.status === 401) { logout(); return; }
        if (!response.ok) throw new Error('Network error');
        const results = await response.json();
        renderAutoSuggestionResults(results);
    } catch (error) {
        console.error('Error fetching autosuggestion results:', error);
        showAutoSuggestionError('Error fetching suggestions.');
    }
}

async function pageResult(query) {
    if (!query) {
        showMessage('Please enter a search query.');
        return;
    }

    const url = new URL(window.location);
    url.searchParams.set('q', query);
    window.history.replaceState({}, '', url);
    $input.val(query);

    showLoading();
    try {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
                'Authorization': 'Token ' + AUTH_TOKEN,
            },
            body: JSON.stringify({ query }),
        });
        if (response.status === 401) { logout(); return; }
        if (!response.ok) throw new Error('Network error');
        const results = await response.json();
        renderSearchResults(results);
    } catch (error) {
        console.error('Error fetching search results:', error);
        showError('Error fetching search results.');
    }
}

$(function () {
    // Inject logout button
    const user = JSON.parse(localStorage.getItem('auth_user') || '{}');
    const username = user.username || 'User';
    const $logoutBar = $(
        `<div class="position-fixed top-0 end-0 p-2 d-flex align-items-center gap-2" style="z-index:1100">` +
        `<small class="text-muted">${username}</small>` +
        `<a href="/profile/me" class="btn btn-sm btn-outline-secondary">My Files</a>` +
        `<button id="logout-btn" class="btn btn-sm btn-outline-secondary">Sign out</button>` +
        `</div>`
    );
    $('body').append($logoutBar);
    $('#logout-btn').on('click', logout);

    if ($input.length === 0) return;

    // Load initial results if query in URL
    const urlParams = new URLSearchParams(window.location.search);
    const initialQuery = urlParams.get('q');
    if (initialQuery) {
        pageResult(initialQuery);
    }

    $input.on('input', function () {
        const query = $input.val().trim();
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => handleSearchQuery(query), DEBOUNCE_MS);
    });

    $input.on('keydown', function (e) {
        if (e.key === 'Enter') {
            clearTimeout(debounceTimer);
            $autoSuggestionResults.empty().addClass('d-none');
            pageResult($input.val().trim());
        }
    });

    if ($button.length) {
        $button.on('click', function () {
            clearTimeout(debounceTimer);
            $autoSuggestionResults.empty().addClass('d-none');
            pageResult($input.val().trim());
        });
    }

    // Hide autosuggestions when clicking outside
    $(document).on('click', function(e) {
        if (!$(e.target).closest('.search-wrapper').length) {
            $autoSuggestionResults.empty().addClass('d-none');
        }
    });
});
