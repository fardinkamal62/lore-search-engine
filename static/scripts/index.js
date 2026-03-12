const AUTH_TOKEN = localStorage.getItem('auth_token');
if (!AUTH_TOKEN) {
    window.location.replace('/login/?next=' + encodeURIComponent(window.location.pathname));
}

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
        showMessage('No matching files found.');
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
});
