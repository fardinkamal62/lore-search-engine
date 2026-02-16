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
            .addClass('list-group-item list-group-item-action flex-column align-items-start')
            .attr('href', `/search?q=${encodeURIComponent(item.title || item.name || 'Untitled')}`);

        const $header = $('<div>').addClass('d-flex w-100 justify-content-between');
        const $h6 = $('<h6>').addClass('mb-1').text(item.title || item.name || 'Untitled');
        $header.append($h6);

        if (item.score !== undefined) {
            const $score = $('<small>').addClass('text-muted').text(Number(item.score).toFixed(2));
            $header.append($score);
        }

        const $p = $('<p>').addClass('mb-1 text-muted small text-truncate').text(item.snippet || item.excerpt || '');
        $a.append($header, $p);

        $container.append($a);
    });

    $autoSuggestionResults.removeClass('d-none').empty().append($container);
}

async function handleSearchQuery(query) {
    if (!query) {
        $autoSuggestionResults.empty().addClass('d-none');
        return;
    }

    $autoSuggestionResults.removeClass('d-none');
    showAutoSuggestionLoading();
    try {
        const response = await fetch(`/api/autocomplete?q=${encodeURIComponent(query)}`);
        if (!response.ok) throw new Error('Network error');
        const results = await response.json();
        renderAutoSuggestionResults(results);
    } catch (error) {
        console.error('Error fetching autosuggestion results:', error);
        showAutoSuggestionError('Error fetching suggestions.');
    }
}

function renderSearchResults(result) {
    if (!result || !Array.isArray(result.results) || result.results.length === 0) {
        showMessage('No results found.');
        return;
    }

    const $container = $('<div>').addClass('list-group w-100');

    result.results.forEach(item => {
        const $item = $('<div>').addClass('list-group-item');

        // Title as clickable link that triggers new search
        const $title = $('<a>')
            .addClass('result-title')
            .attr('href', '#')
            .text(item.title || 'Untitled')
            .on('click', function(e) {
                e.preventDefault();
                // Trigger new search with this title
                handleSearchQuery(item.title || 'Untitled');
            });

        // Resource name and score
        const $meta = $('<div>').addClass('result-meta');
        if (item['resource-name']) {
            $meta.append($('<span>').text(item['resource-name']));
        }
        if (item.score !== undefined) {
            $meta.append($('<span>').addClass('float-end').text('Score: ' + Number(item.score).toFixed(2)));
        }

        // Description
        const $description = $('<p>')
            .addClass('result-description')
            .text(item.description || '');

        // Categories
        const $categories = $('<div>');
        if (item.category && Array.isArray(item.category)) {
            item.category.forEach(cat => {
                $categories.append(
                    $('<span>').addClass('result-category').text(cat)
                );
            });
        }

        $item.append($title, $meta, $description, $categories);
        $container.append($item);
    });

    $results.empty().append($container);
}

async function pageResult(query) {
    if (!query) {
        showMessage('Please enter a search query.');
        return;
    }

    // Update URL without reload
    const url = new URL(window.location);
    url.searchParams.set('q', query);
    window.history.replaceState({}, '', url);

    // Update input field
    $input.val(query);

    showLoading();
    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': $('[name=csrfmiddlewaretoken]').val() || document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
            },
            body: JSON.stringify({ query: query })
        });
        if (!response.ok) throw new Error('Network error');
        const results = await response.json();
        renderSearchResults(results);
    } catch (error) {
        console.error('Error fetching search results:', error);
        showError('Error fetching search results.');
    }
}

$(function () {
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
