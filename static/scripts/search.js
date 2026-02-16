const DEBOUNCE_MS = 250;
let debounceTimer = null;

// jQuery-wrapped DOM refs
const $input = $('#search-input');
const $results = $('#search-results');
const $button = $('#search');

function showLoading() {
    $results.html('<div class="text-center my-5"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>');
}

function showMessage(text) {
    $results.html('<div class="text-muted text-center mt-5">' + text + '</div>');
}

function showError(text) {
    $results.html('<div class="alert alert-danger">' + text + '</div>');
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

async function handleSearchQuery(query) {
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
        handleSearchQuery(initialQuery);
    }

    // Only trigger search on Enter key or button click, not on input
    $input.on('keydown', function (e) {
        if (e.key === 'Enter') {
            handleSearchQuery($input.val().trim());
        }
    });

    if ($button.length) {
        $button.on('click', function () {
            handleSearchQuery($input.val().trim());
        });
    }
});
