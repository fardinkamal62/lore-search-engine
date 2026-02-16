const DEBOUNCE_MS = 250;
let debounceTimer = null;

// jQuery-wrapped DOM refs
const $input = $('#search-input');
const $results = $('#search-results');
const $button = $('#search');

function showLoading() {
    $results.html('<div class="text-center my-3"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>');
}
function showMessage(text) {
    $results.html('<div class="text-muted text-center mt-2">' + text + '</div>');
}
function showError(text) {
    $results.html('<div class="alert alert-danger">' + text + '</div>');
}

function renderResults(result) {
    if (!result || !Array.isArray(result.suggestions) || result.suggestions.length === 0) {
        showMessage('No results found.');
        return;
    }

    const $container = $('<div>').addClass('list-group w-100');

    result.suggestions.forEach(item => {
        const $a = $('<a>')
            .addClass('list-group-item list-group-item-action flex-cscriptsolumn align-items-start')
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

    $results.removeClass('d-none').empty().append($container);
}

async function handleSearchQuery(query) {
    if (!query) {
        $results.empty().addClass('d-none');
        return;
    }

    $results.removeClass('d-none');
    showLoading();
    try {
        const response = await fetch(`/api/autocomplete?q=${encodeURIComponent(query)}`);
        if (!response.ok) throw new Error('Network error');
        const results = await response.json();
        renderResults(results);
    } catch (error) {
        console.error('Error fetching search results:', error);
        showError('Error fetching results.');
    }
}

$(function () {
    if ($input.length === 0) return;

    $input.on('input', function () {
        const q = $input.val().trim();
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => handleSearchQuery(q), DEBOUNCE_MS);
    });

    $input.on('keydown', function (e) {
        if (e.key === 'Enter') {
            clearTimeout(debounceTimer);
            // Navigate to search page on Enter
            const query = $input.val().trim();
            if (query) {
                window.location.href = `/search?q=${encodeURIComponent(query)}`;
            }
        }
    });

    if ($button.length) {
        $button.on('click', function () {
            clearTimeout(debounceTimer);
            // Navigate to search page on button click
            const query = $input.val().trim();
            if (query) {
                window.location.href = `/search?q=${encodeURIComponent(query)}`;
            }
        });
    }
});
