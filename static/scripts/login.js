// Redirect to home if already logged in
if (localStorage.getItem('auth_token')) {
    window.location.replace('/');
}

const $form     = $('#login-form');
const $username = $('#username');
const $password = $('#password');
const $btnText  = $('#btn-text');
const $spinner  = $('#btn-spinner');
const $error    = $('#error-alert');
const $btn      = $('#login-btn');

function showError(msg) {
    $error.text(msg).removeClass('d-none');
}

function hideError() {
    $error.addClass('d-none').text('');
}

function setLoading(on) {
    $btn.prop('disabled', on);
    $btnText.text(on ? 'Signing in…' : 'Sign in');
    $spinner.toggleClass('d-none', !on);
}

$form.on('submit', async function (e) {
    e.preventDefault();
    hideError();

    const username = $username.val().trim();
    const password = $password.val();

    if (!username || !password) {
        showError('Please enter both username and password.');
        return;
    }

    setLoading(true);
    try {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
        const response = await fetch('/api/auth/login/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({ username, password }),
        });

        const data = await response.json();

        if (!response.ok) {
            const msg = data?.errors?.non_field_errors?.[0]
                || data?.message
                || 'Invalid username or password.';
            showError(msg);
            return;
        }

        // Persist token and user info
        localStorage.setItem('auth_token', data.token);
        localStorage.setItem('auth_user', JSON.stringify(data.user));

        // Go to the page they were trying to reach, or home
        const next = new URLSearchParams(window.location.search).get('next') || '/';
        window.location.replace(next);

    } catch (err) {
        console.error('Login error:', err);
        showError('Something went wrong. Please try again.');
    } finally {
        setLoading(false);
    }
});

