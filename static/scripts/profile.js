// Auth guard
const AUTH_TOKEN = localStorage.getItem('auth_token');
if (!AUTH_TOKEN) {
    window.location.replace('/login/?next=' + encodeURIComponent(window.location.pathname));
}

const AUTH_USER   = JSON.parse(localStorage.getItem('auth_user') || '{}');
const CSRF_TOKEN  = () => document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

// Bootstrap modal instances (initialised after DOM ready)
let renameModal, deleteModal;

// ── Helpers ───────────────────────────────────────────────────────────────

function formatBytes(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function formatDate(iso) {
    return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

const FILE_ICONS = {
    pdf:  { icon: 'fa-file-pdf',  color: '#e74c3c' },
    docx: { icon: 'fa-file-word', color: '#2980b9' },
    png:  { icon: 'fa-file-image',color: '#27ae60' },
    jpg:  { icon: 'fa-file-image',color: '#27ae60' },
    md:   { icon: 'fa-file-lines',color: '#8e44ad' },
};

function statusBadge(s) {
    const label = s.charAt(0).toUpperCase() + s.slice(1);
    return `<span class="badge badge-status badge-status-${s}">${label}</span>`;
}

function logout() {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    window.location.replace('/login/');
}

// ── Render file list ──────────────────────────────────────────────────────

function renderFiles(files) {
    const $list = $('#file-list');

    // Update stats
    const total     = files.length;
    const indexed   = files.filter(f => f.status === 'processed').length;
    const pending   = files.filter(f => f.status === 'pending').length;
    $('#stats-label').text(`${total} file${total !== 1 ? 's' : ''} · ${indexed} indexed · ${pending} pending`);

    if (total === 0) {
        $list.html(
            '<div class="empty-state">' +
            '<i class="fa-solid fa-folder-open d-block"></i>' +
            '<p class="mb-2 fw-medium">No files yet</p>' +
            '<p class="small">Upload your first file using the button above.</p>' +
            '</div>'
        );
        return;
    }

    $list.empty();
    files.forEach(file => $list.append(buildCard(file)));
}

function buildCard(file) {
    const meta    = FILE_ICONS[file.file_type] || { icon: 'fa-file', color: '#6c757d' };
    const $card   = $('<div>').addClass('file-card').attr('data-file-id', file.id);

    // Icon
    const $icon = $('<div>').addClass('file-icon')
        .html(`<i class="fa-solid ${meta.icon}" style="color:${meta.color}"></i>`);

    // Info
    const $info = $('<div>').addClass('file-info');
    const $name = $('<a>')
        .addClass('file-name')
        .attr('href', file.file_url || '#')
        .attr('target', '_blank')
        .attr('rel', 'noopener noreferrer')
        .text(file.original_filename);

    const $meta = $('<div>').addClass('file-meta').html(
        statusBadge(file.status) +
        `<span>${file.file_type.toUpperCase()}</span>` +
        `<span>${formatBytes(file.file_size)}</span>` +
        `<span>${formatDate(file.uploaded_at)}</span>`
    );
    $info.append($name, $meta);

    // Actions
    const $actions = $('<div>').addClass('file-actions');

    const $rename = $('<button>')
        .addClass('btn btn-outline-secondary')
        .attr('title', 'Rename')
        .html('<i class="fa-solid fa-pen-to-square"></i>')
        .on('click', () => openRenameModal(file));

    const $del = $('<button>')
        .addClass('btn btn-outline-danger')
        .attr('title', 'Delete')
        .html('<i class="fa-solid fa-trash"></i>')
        .on('click', () => openDeleteModal(file));

    $actions.append($rename, $del);
    $card.append($icon, $info, $actions);
    return $card;
}

// ── Fetch files ───────────────────────────────────────────────────────────

async function loadFiles() {
    try {
        const resp = await fetch('/api/upload/', {
            headers: { 'Authorization': 'Token ' + AUTH_TOKEN },
        });
        if (resp.status === 401) { logout(); return; }
        if (!resp.ok) throw new Error('Failed to load files.');
        const data = await resp.json();
        renderFiles(data.files || []);
    } catch (err) {
        $('#file-list').html('<div class="alert alert-danger">Failed to load files. Please refresh.</div>');
        console.error(err);
    }
}

// ── Rename ────────────────────────────────────────────────────────────────

function openRenameModal(file) {
    $('#rename-file-id').val(file.id);
    $('#rename-input').val(file.original_filename);
    $('#rename-error').addClass('d-none').text('');
    renameModal.show();
}

async function saveRename() {
    const fileId  = $('#rename-file-id').val();
    const newName = $('#rename-input').val().trim();
    const $err    = $('#rename-error');

    if (!newName) {
        $err.text('Filename must not be empty.').removeClass('d-none');
        return;
    }
    $err.addClass('d-none');

    const $btn = $('#rename-save-btn').prop('disabled', true).text('Saving…');
    try {
        const resp = await fetch(`/api/upload/${fileId}/`, {
            method: 'PATCH',
            headers: {
                'Authorization': 'Token ' + AUTH_TOKEN,
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF_TOKEN(),
            },
            body: JSON.stringify({ original_filename: newName }),
        });
        if (resp.status === 401) { logout(); return; }
        const data = await resp.json();
        if (!resp.ok) {
            $err.text(data.error || 'Rename failed.').removeClass('d-none');
            return;
        }
        // Update card in-place
        $(`[data-file-id="${fileId}"] .file-name`).text(data.original_filename);
        renameModal.hide();
    } catch (err) {
        $err.text('Network error. Please try again.').removeClass('d-none');
    } finally {
        $btn.prop('disabled', false).text('Save');
    }
}

// ── Delete ────────────────────────────────────────────────────────────────

function openDeleteModal(file) {
    $('#delete-file-id').val(file.id);
    $('#delete-file-name').text(file.original_filename);
    deleteModal.show();
}

async function confirmDelete() {
    const fileId = $('#delete-file-id').val();
    const $btn   = $('#delete-confirm-btn').prop('disabled', true).text('Deleting…');

    try {
        const resp = await fetch(`/api/upload/${fileId}/`, {
            method: 'DELETE',
            headers: {
                'Authorization': 'Token ' + AUTH_TOKEN,
                'X-CSRFToken': CSRF_TOKEN(),
            },
        });
        if (resp.status === 401) { logout(); return; }
        if (!resp.ok) { alert('Delete failed. Please try again.'); return; }

        // Remove card and refresh stats
        $(`[data-file-id="${fileId}"]`).fadeOut(200, function () {
            $(this).remove();
            refreshStats();
        });
        deleteModal.hide();
    } catch (err) {
        alert('Network error. Please try again.');
    } finally {
        $btn.prop('disabled', false).text('Delete');
    }
}

function refreshStats() {
    const cards = $('.file-card').length;
    $('#stats-label').text(`${cards} file${cards !== 1 ? 's' : ''}`);
    if (cards === 0) {
        $('#file-list').html(
            '<div class="empty-state">' +
            '<i class="fa-solid fa-folder-open d-block"></i>' +
            '<p class="mb-2 fw-medium">No files yet</p>' +
            '<p class="small">Upload your first file using the button above.</p>' +
            '</div>'
        );
    }
}

// ── Upload ────────────────────────────────────────────────────────────────

function makeStatusRow(name) {
    const $row    = $('<div>').addClass('upload-item');
    const $icon   = $('<i>').addClass('fa-solid fa-file-arrow-up text-muted');
    const $label  = $('<span>').addClass('upload-name').text(name);
    const $status = $('<span>').addClass('upload-status text-muted').text('Uploading…');
    $row.append($icon, $label, $status);
    $('#upload-list').prepend($row);
    return { $row, $icon, $status };
}

async function uploadFiles(fileList) {
    if (!fileList || !fileList.length) return;

    const files = Array.from(fileList);
    const rows  = files.map(f => ({ file: f, ...makeStatusRow(f.name) }));

    const formData = new FormData();
    files.forEach(f => formData.append('files', f));

    try {
        const resp = await fetch('/api/upload/', {
            method: 'POST',
            headers: {
                'Authorization': 'Token ' + AUTH_TOKEN,
                'X-CSRFToken': CSRF_TOKEN(),
            },
            body: formData,
        });
        if (resp.status === 401) { logout(); return; }

        const data = await resp.json();
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

        // Refresh the file list to show new uploads
        if (data.files && data.files.length) {
            setTimeout(loadFiles, 600);
        }
    } catch (err) {
        rows.forEach(({ $icon, $status }) => {
            $icon.removeClass('fa-file-arrow-up text-muted').addClass('fa-circle-xmark text-danger');
            $status.removeClass('text-muted').addClass('text-danger').text('Network error');
        });
    }
}

// ── Boot ──────────────────────────────────────────────────────────────────

$(function () {
    // Nav
    $('#nav-username').text(AUTH_USER.username || '');
    $('#logout-btn').on('click', logout);

    // Bootstrap modals
    renameModal = new bootstrap.Modal(document.getElementById('rename-modal'));
    deleteModal = new bootstrap.Modal(document.getElementById('delete-modal'));

    // Modal actions
    $('#rename-save-btn').on('click', saveRename);
    $('#rename-input').on('keydown', e => { if (e.key === 'Enter') saveRename(); });
    $('#delete-confirm-btn').on('click', confirmDelete);

    // Upload panel toggle
    $('#open-upload-btn').on('click', () => {
        $('#upload-panel').toggleClass('d-none');
    });

    // Drop zone
    const $dropZone  = $('#drop-zone');
    const $fileInput = $('#file-input');

    $dropZone.on('click keydown', function (e) {
        if (e.type === 'click' || e.key === 'Enter' || e.key === ' ') $fileInput.trigger('click');
    });
    $dropZone.on('dragover dragenter', e => { e.preventDefault(); $dropZone.addClass('drag-over'); });
    $dropZone.on('dragleave drop', function (e) {
        e.preventDefault();
        $dropZone.removeClass('drag-over');
        if (e.type === 'drop') uploadFiles(e.originalEvent.dataTransfer.files);
    });
    $fileInput.on('change', function () { uploadFiles(this.files); this.value = ''; });

    // Initial load
    loadFiles();
});

