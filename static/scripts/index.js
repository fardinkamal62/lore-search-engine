const AUTH_TOKEN = localStorage.getItem('auth_token');
if (!AUTH_TOKEN) {
    window.location.replace('/login/?next=' + encodeURIComponent(window.location.pathname));
}

const DEBOUNCE_MS = 250;
let debounceTimer = null;
let activeSuggestionIndex = -1;   // -1 = nothing highlighted

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

function resetSuggestionIndex() {
    activeSuggestionIndex = -1;
    $results.find('.list-group-item').removeClass('active');
}

function highlightSuggestion(index) {
    const $items = $results.find('.list-group-item');
    const total  = $items.length;
    if (!total) return;
    activeSuggestionIndex = Math.max(-1, Math.min(index, total - 1));
    $items.removeClass('active');
    if (activeSuggestionIndex >= 0) {
        $items.eq(activeSuggestionIndex).addClass('active');
    }
}

function renderResults(result) {
    if (!result || !Array.isArray(result.suggestions) || result.suggestions.length === 0) {
        $results.empty().addClass('d-none');
        resetSuggestionIndex();
        return;
    }

    const $container = $('<div>').addClass('list-group w-100');

    result.suggestions.forEach(item => {
        const phrase = item.phrase || '';
        const $a = $('<a>')
            .addClass('list-group-item list-group-item-action d-flex align-items-center gap-2')
            .attr('href', `/search?q=${encodeURIComponent(phrase)}`)
            .attr('data-phrase', phrase)
            .on('mouseenter', function () {
                const idx = $results.find('.list-group-item').index(this);
                highlightSuggestion(idx);
            });

        const $icon = $('<i>').addClass('fa-solid fa-magnifying-glass text-muted flex-shrink-0').css('font-size', '0.75rem');
        const $text = $('<span>').addClass('flex-grow-1').text(phrase);

        $a.append($icon, $text);
        $container.append($a);
    });

    resetSuggestionIndex();
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
        const response = await fetch(`/api/autocomplete?q=${encodeURIComponent(query)}`, {
            headers: { 'Authorization': 'Token ' + AUTH_TOKEN },
        });
        if (response.status === 401) { logout(); return; }
        if (!response.ok) throw new Error('Network error');
        const results = await response.json();
        renderResults(results);
    } catch (error) {
        console.error('Error fetching search results:', error);
        showError('Error fetching results.');
    }
}

function logout() {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    window.location.replace('/login/');
}

$(function () {
    // Inject logout button into the page
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

    $input.on('input', function () {
        const q = $input.val().trim();
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => handleSearchQuery(q), DEBOUNCE_MS);
    });

    $input.on('keydown', function (e) {
        const $items = $results.find('.list-group-item');
        const dropdownOpen = !$results.hasClass('d-none') && $items.length > 0;

        if (e.key === 'ArrowDown') {
            if (!dropdownOpen) return;
            e.preventDefault();
            highlightSuggestion(activeSuggestionIndex + 1);
            return;
        }

        if (e.key === 'ArrowUp') {
            if (!dropdownOpen) return;
            e.preventDefault();
            highlightSuggestion(activeSuggestionIndex - 1);
            return;
        }

        if (e.key === 'Escape') {
            $results.empty().addClass('d-none');
            resetSuggestionIndex();
            return;
        }

        if (e.key === 'Enter') {
            clearTimeout(debounceTimer);
            if (dropdownOpen && activeSuggestionIndex >= 0) {
                const phrase = $items.eq(activeSuggestionIndex).data('phrase');
                $results.empty().addClass('d-none');
                resetSuggestionIndex();
                window.location.href = `/search?q=${encodeURIComponent(phrase)}`;
                return;
            }
            const query = $input.val().trim();
            if (query) {
                $results.empty().addClass('d-none');
                resetSuggestionIndex();
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

    // ── Upload ────────────────────────────────────────────────────────────
    const $dropZone   = $('#drop-zone');
    const $fileInput  = $('#file-input');
    const $uploadList = $('#upload-list');

    if ($dropZone.length) {
        $dropZone.on('click keydown', function (e) {
            if (e.type === 'click' || e.key === 'Enter' || e.key === ' ') {
                $fileInput.trigger('click');
            }
        });

        $dropZone.on('dragover dragenter', function (e) {
            e.preventDefault();
            $dropZone.addClass('drag-over');
        });
        $dropZone.on('dragleave drop', function (e) {
            e.preventDefault();
            $dropZone.removeClass('drag-over');
            if (e.type === 'drop') {
                uploadFiles(e.originalEvent.dataTransfer.files);
            }
        });

        $fileInput.on('change', function () {
            uploadFiles(this.files);
            this.value = '';
        });
    }

    function makeStatusRow(name) {
        const $row    = $('<div>').addClass('upload-item');
        const $icon   = $('<i>').addClass('fa-solid fa-file-arrow-up text-muted');
        const $label  = $('<span>').addClass('upload-name').text(name);
        const $status = $('<span>').addClass('upload-status text-muted').text('Uploading…');
        $row.append($icon, $label, $status);
        $uploadList.prepend($row);
        return { $row, $icon, $status };
    }

    async function uploadFiles(fileList) {
        if (!fileList || !fileList.length) return;

        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
        const files = Array.from(fileList);
        const rows  = files.map(f => ({ file: f, ...makeStatusRow(f.name) }));

        const formData = new FormData();
        files.forEach(f => formData.append('files', f));

        try {
            const response = await fetch('/api/upload/', {
                method: 'POST',
                headers: {
                    'Authorization': 'Token ' + AUTH_TOKEN,
                    'X-CSRFToken': csrfToken,
                },
                body: formData,
            });

            if (response.status === 401) { logout(); return; }

            const data = await response.json();
            const savedNames = new Set((data.files || []).map(f => f.original_filename));
            const failedMap  = {};
            (data.failed || []).forEach(f => {
                failedMap[f.filename] = Object.values(f.errors || {}).flat().join(', ');
            });

            rows.forEach(({ file, $icon, $status }) => {
                if (savedNames.has(file.name)) {
                    $icon.removeClass('fa-file-arrow-up text-muted').addClass('fa-circle-check text-success');
                    $status.removeClass('text-muted').addClass('text-success').text('Queued for indexing');
                } else {
                    $icon.removeClass('fa-file-arrow-up text-muted').addClass('fa-circle-xmark text-danger');
                    $status.removeClass('text-muted').addClass('text-danger').text(failedMap[file.name] || 'Upload failed');
                }
            });
        } catch (err) {
            console.error('Upload error:', err);
            rows.forEach(({ $icon, $status }) => {
                $icon.removeClass('fa-file-arrow-up text-muted').addClass('fa-circle-xmark text-danger');
                $status.removeClass('text-muted').addClass('text-danger').text('Network error');
            });
        }
    }
    // ─────────────────────────────────────────────────────────────────────

    // Hide autosuggestions when clicking outside
    $(document).on('click', function(e) {
        if (!$(e.target).closest('.search-wrapper').length) {
            $results.empty().addClass('d-none');
            resetSuggestionIndex();
        }
    });
});
