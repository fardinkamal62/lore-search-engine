# Lore Search Engine — Codebase Documentation

> **Last updated:** March 22, 2026  
> **Stack:** Django 6 · Django REST Framework · PostgreSQL · Bootstrap 5 · jQuery · PyPDF2 · python-docx · NLTK · pytesseract

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Repository Structure](#2-repository-structure)
3. [Technology Stack & Dependencies](#3-technology-stack--dependencies)
4. [Configuration & Environment](#4-configuration--environment)
5. [Application Modules](#5-application-modules)
   - 5.1 [Backend Core (`backend/`)](#51-backend-core-backend)
   - 5.2 [Authentication App (`apps/authentication/`)](#52-authentication-app-appsauthentication)
   - 5.3 [Upload App (`apps/upload/`)](#53-upload-app-appsupload)
   - 5.4 [Indexer App (`apps/indexer/`)](#54-indexer-app-appsindexer)
6. [API Reference](#6-api-reference)
   - 6.1 [Frontend / Page Routes](#61-frontend--page-routes)
   - 6.2 [Search API](#62-search-api)
   - 6.3 [Authentication API](#63-authentication-api)
   - 6.4 [Upload API](#64-upload-api)
7. [Data Models](#7-data-models)
8. [Frontend](#8-frontend)
9. [Error Handling](#9-error-handling)
10. [Deployment](#10-deployment)
11. [Testing](#12-testing)

---

## 1. Project Overview

**Lore** is a personal search engine backend that allows users to upload documents (PDFs, Word documents, text files, images, Markdown files), index them, and search through their content. The system is designed to eventually support an inverted index, a Trie-based autocomplete engine, and a knowledge-graph visualization of document relationships.

The current implementation provides:
- User registration, login, logout, and token management
- Authenticated file upload (single or multiple files at once) with validation and soft-delete
- **Automatic document indexing** — files are indexed in a background thread immediately after upload, building a TF-IDF inverted index stored in PostgreSQL
- **Document search** — `POST /api/search` queries the inverted index and returns the user's matching files ranked by TF-IDF score; each result links directly to the file; returns a clear "no match" message when nothing is found
- **Autocomplete** — `GET /api/autocomplete` uses a Trie-backed prefix engine (filenames + indexed phrases) and returns up to 8 phrase suggestions in real time
- **Profile page** — `/profile/me` lets users view, upload, rename, and delete their own files
- A server-side rendered home page, search results page, and profile page backed by a REST API

---

## 2. Repository Structure

```
lore-search-engine/
├── manage.py                    # Django management entry point
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Docker image definition
├── compose.yml                  # Docker Compose (app + PostgreSQL)
├── .env.example                 # Environment variable template
│
├── backend/                     # Django project package
│   ├── settings.py              # Project settings
│   ├── urls.py                  # Root URL configuration
│   ├── views.py                 # Page and core API views
│   ├── models.py                # (empty – reserved)
│   ├── serializers.py           # (empty – reserved)
│   ├── asgi.py / wsgi.py        # ASGI / WSGI entry points
│
├── apps/
│   ├── authentication/          # User auth app
│   │   ├── views.py             # Register, Login, Logout, Profile, TokenRefresh
│   │   ├── serializers.py       # UserRegistration, UserLogin, User serializers
│   │   ├── services.py          # AuthenticationService, PermissionService
│   │   ├── utils.py             # AuthUtils, UserUtils helpers
│   │   ├── exceptions.py        # Custom DRF exception handler
│   │   ├── urls.py              # Auth URL patterns
│   │   ├── models.py            # (empty – uses Django's built-in User)
│   │   └── tests.py             # Auth API tests
│   │
│   └── upload/                  # File upload app
│       ├── views.py             # FileUploadListView, FileDetailDeleteView
│       ├── serializers.py       # FileUploadSerializer, UploadedFileSerializer
│       ├── models.py            # UploadedFile model
│       ├── services.py          # FileUploadService (triggers background indexing on upload)
│       ├── utils.py             # UploadUtils (validation helpers)
│       ├── exceptions.py        # Custom upload exceptions
│       ├── admin.py             # Django admin registration
│       ├── urls.py              # Upload URL patterns
│       ├── tests.py             # Upload & auth integration tests
│       └── migrations/          # Database migrations
│   │
│   └── indexer/                 # Document indexing app
│       ├── models.py            # InvertedIndex model (single index table)
│       ├── extractor.py         # Text extraction per file type (PDF/DOCX/MD/TXT/image)
│       ├── tokenizer.py         # Lowercasing, stop-word removal, Porter stemming
│       ├── trie.py              # PrefixTrie implementation for autocomplete
│       ├── pipeline.py          # index_document() — full indexing orchestration
│       ├── services.py          # IndexerService (user-scoped search & query helpers)
│       ├── admin.py             # Django admin registration
│       ├── migrations/          # Database migrations
│       └── management/
│           └── commands/
│               └── reindex.py   # CLI: backfill / full corpus re-score
│
├── static/                      # Frontend assets (served by Django)
│   ├── home_page.html           # Home / search entry page (search + drag-and-drop upload)
│   ├── search_page.html         # Search results page
│   ├── profile_page.html        # User profile — file management (upload, rename, delete)
│   ├── scripts/
│   │   ├── index.js             # Home page JS (autocomplete, upload, navigation)
│   │   ├── search.js            # Search results page JS
│   │   └── profile.js           # Profile page JS (file list, rename modal, delete modal, upload)
│   └── styles/
│       ├── index.css
│       ├── search.css
│       └── profile.css
│
├── media/uploads/               # User-uploaded files (runtime)
├── data/                        # Reserved for index data
├── logs/                        # Application logs
└── docs/                        # Documentation
```

---

## 3. Technology Stack & Dependencies

| Package               | Version  | Purpose                            |
|-----------------------|----------|------------------------------------|
| `django`              | ≥ 6.0    | Web framework                      |
| `djangorestframework` | ≥ 3.16.1 | REST API layer                     |
| `django-environ`      | ≥ 0.12.0 | `.env` file configuration          |
| `psycopg2-binary`     | ≥ 2.9.0  | PostgreSQL driver                  |
| `django-cors-headers` | ≥ 4.0.0  | CORS policy management             |
| `Pillow`              | ≥ 10.0.0 | Image handling / OCR input         |
| `PyPDF2`              | ≥ 3.0.0  | PDF text extraction                |
| `python-docx`         | ≥ 1.1.0  | DOCX text extraction               |
| `nltk`                | ≥ 3.8.0  | Tokenization, stop-words, stemming |
| `pytesseract`         | ≥ 0.3.10 | OCR for PNG/JPG images             |
| `pytest`              | ≥ 9.0.2  | Test runner                        |
| `pytest-django`       | ≥ 4.11.0 | Django integration for pytest      |
| `pytest-cov`          | ≥ 7.0.0  | Test coverage reporting            |

**Frontend libraries** (loaded from CDN):

| Library       | Version | Purpose          |
|---------------|---------|------------------|
| Bootstrap     | 5.3.8   | UI framework     |
| jQuery (slim) | 3.7.1   | DOM manipulation |
| Font Awesome  | 7.0.1   | Icons            |

---

## 4. Configuration & Environment

All configuration is loaded from a `.env` file via `django-environ`. Refer to `.env.example` for the full template.

| Variable        | Required | Default               | Description                   |
|-----------------|----------|-----------------------|-------------------------------|
| `SECRET_KEY`    | ✅        | —                     | Django secret key             |
| `DEBUG`         | ✅        | `False`               | Debug mode toggle             |
| `ALLOWED_HOSTS` | ✅        | `localhost,127.0.0.1` | Comma-separated allowed hosts |
| `DB_NAME`       | ✅        | —                     | PostgreSQL database name      |
| `DB_USER`       | ✅        | —                     | PostgreSQL user               |
| `DB_PASSWORD`   | ✅        | —                     | PostgreSQL password           |
| `DB_HOST`       | ❌        | `localhost`           | PostgreSQL host               |
| `DB_PORT`       | ❌        | `5432`                | PostgreSQL port               |
| `NLTK_DATA`     | ❌        | `data/nltk`           | Path for NLTK corpus data     |

### Key DRF Settings

| Setting                | Value                                                     |
|------------------------|-----------------------------------------------------------|
| Default authentication | `TokenAuthentication`                                     |
| Default permission     | `IsAuthenticated`                                         |
| Pagination class       | `PageNumberPagination`                                    |
| Page size              | `20`                                                      |
| Parsers                | `JSON`, `Form`, `MultiPart`                               |
| Exception handler      | `apps.authentication.exceptions.custom_exception_handler` |

### CORS

- **Allowed origins (production):** `http://localhost:3000`, `http://127.0.0.1:3000`, `http://localhost:8080`, `http://127.0.0.1:8080`
- **Development:** `CORS_ALLOW_ALL_ORIGINS = True` when `DEBUG=True`
- Credentials are allowed (`CORS_ALLOW_CREDENTIALS = True`)

---

## 5. Application Modules

### 5.1 Backend Core (`backend/`)

The project package containing settings, root URLs, and the core API views.

#### `backend/views.py`

| View function   | Route                   | Description                                                                                                           |
|-----------------|-------------------------|-----------------------------------------------------------------------------------------------------------------------|
| `home_page`     | `GET /`                 | Renders `home_page.html` with a `timestamp` context variable                                                          |
| `search_page`   | `GET /search/`          | Renders `search_page.html` with `timestamp` and `query` context variables                                             |
| `profile_page`  | `GET /profile/me`       | Renders `profile_page.html`; auth-guarded client-side                                                                 |
| `auto_complete` | `GET /api/autocomplete` | Authenticates via Token header; uses `AutocompleteService` + `PrefixTrie` to return up to 8 prefix phrase suggestions |
| `search`        | `POST /api/search`      | Authenticates via Token header, queries `IndexerService`, returns ranked file results                                 |

All page views set `no-cache` headers to prevent stale static assets during development.

---

### 5.2 Authentication App (`apps/authentication/`)

Handles user registration, login, logout, profile management, and token lifecycle. Uses Django's built-in `User` model and DRF's `Token` model — no custom user model is defined.


#### `PermissionService` — Role Matrix

| Permission           | admin | editor | contributor | viewer |
|----------------------|-------|--------|-------------|--------|
| `can_manage_users`   | ✅     | ❌      | ❌           | ❌      |
| `can_manage_content` | ✅     | ✅      | ❌           | ❌      |
| `can_view_analytics` | ✅     | ❌      | ❌           | ❌      |
| `can_manage_system`  | ✅     | ❌      | ❌           | ❌      |
| `can_upload_files`   | ✅     | ✅      | ✅           | ❌      |
| `can_search`         | ✅     | ✅      | ✅           | ✅      |

> **Note:** Role assignment is not yet wired to the `User` model. The service currently defaults all authenticated non-superusers to the `viewer` role.

---

### 5.3 Upload App (`apps/upload/`)

Handles secure file uploads, per-user file listing, individual file retrieval, rename, and soft-deletion.  
`FileUploadService.save_file()` spawns a background thread to index the file immediately after it is persisted. On soft-delete, index entries for that file are purged automatically.

The `POST /api/upload/` endpoint accepts **multiple files** in a single request (field name `files`). Each file is validated individually; results are returned as `files` (saved) and `failed` arrays.

`FileUploadService.rename_file()` renames both the `original_filename` field and the actual file on disk (`os.rename`), then updates the `file` field in the database to reflect the new path. It guards against clobbering an existing file.

#### `UploadUtils` — Constraints

| Constraint          | Value                                            |
|---------------------|--------------------------------------------------|
| Allowed extensions  | `pdf`, `docx`, `png`, `jpg`, `jpeg`, `md`, `txt` |
| Max file size       | **20 MB**                                        |
| Extension alias     | `jpeg` → `jpg` (stored canonically as `jpg`)     |
| Upload path pattern | `media/uploads/YYYY/MM/DD/`                      |

---

### 5.4 Indexer App (`apps/indexer/`)

Provides automated document indexing, building a TF-IDF inverted index stored in a single PostgreSQL table. Indexing is triggered in a **daemon background thread** immediately after every upload (fire-and-forget, non-blocking). Designed so the thread call can be replaced with a `celery.delay()` in one line when a task queue is added.

User isolation is enforced implicitly on every query via `document__uploaded_by=user` — no extra ownership column is needed.

#### Indexing Pipeline

```
UploadedFile (status=pending)
    → extractor.extract_text()     # dispatch on file_type
    → tokenizer.tokenize_with_positions()  # lowercase → stop-words → Porter stem
    → compute TF per term
    → fetch corpus document_frequency (user-scoped, eventual consistency)
    → compute smoothed TF-IDF
    → InvertedIndex.bulk_create(update_conflicts=True)
    → UploadedFile.status = 'processed'  (or 'failed' on error)
```

#### `extractor.py` — File Type Dispatch

| File type     | Library                  | Notes                                                                                                       |
|---------------|--------------------------|-------------------------------------------------------------------------------------------------------------|
| `pdf`         | `PyPDF2`                 | Extracts text from all pages                                                                                |
| `docx`        | `python-docx`            | Extracts paragraph text                                                                                     |
| `md` / `txt`  | built-in `open()`        | UTF-8 read, errors replaced                                                                                 |
| `png` / `jpg` | `pytesseract` + `Pillow` | OCR; requires `tesseract-ocr` binary on host. Logs a warning and returns `""` if Tesseract is not installed |

#### `tokenizer.py` — Token Pipeline

1. `word_tokenize` (NLTK punkt)
2. Keep only alphabetic tokens
3. Remove English stop-words (NLTK corpus, downloaded to `NLTK_DATA`)
4. Porter-stem each token

#### `services.py` — `IndexerService`

| Method                                 | Description                                                                               |
|----------------------------------------|-------------------------------------------------------------------------------------------|
| `search(user, query, limit)`           | Tokenize query, match terms against user's corpus, return results ranked by summed TF-IDF |
| `get_document_index(user, file_id)`    | All index entries for one file (user-scoped)                                              |
| `get_index_stats(user)`                | `total_entries`, `unique_terms`, `indexed_documents` counts                               |
| `delete_document_index(user, file_id)` | Delete all index rows for a file; called automatically on soft-delete                     |

#### `services.py` — `AutocompleteService`

| Method                        | Description                                                                                 |
|-------------------------------|---------------------------------------------------------------------------------------------|
| `get_suggestions(user, q, n)` | Builds a user-scoped Trie from filename/content phrases and returns top `n` prefix matches  |
| `_filename_phrases(filename)` | Normalizes filename and emits phrase windows used as Trie entries                           |
| `_build_user_trie(user)`      | Loads `UploadedFile` + `DocumentPhrase` rows and inserts weighted entries into `PrefixTrie` |

#### `management/commands/reindex.py`

CLI tool for backfilling and corpus re-scoring:

```bash
# Index a single file (resets status to pending, clears old entries)
python manage.py reindex --file-id 42

# Index all pending/failed files (optionally scoped to one user)
python manage.py reindex --pending [--user fardin]

# Full corpus re-score — fixes TF-IDF drift from eventual consistency
python manage.py reindex --all [--user fardin]
```

---

## 6. API Reference

### Authentication

All endpoints under `/api/auth/` that are **not** listed as public require a DRF Token in the `Authorization` header:

```
Authorization: Token <your_token_here>
```

All endpoints under `/api/upload/` require authentication.

---

### 6.1 Frontend / Page Routes

#### `GET /`
Renders the home page.

**Response:** HTML — `home_page.html`

---

#### `GET /search/`
Renders the search results page.

**Query Parameters:**

| Parameter | Type   | Required | Description                                       |
|-----------|--------|----------|---------------------------------------------------|
| `q`       | string | ❌        | Initial search query pre-filled in the search box |

**Response:** HTML — `search_page.html`

---

#### `GET /profile/me`
Renders the profile page for the currently authenticated user.

**Authentication:** Token is validated client-side in `profile.js`; unauthenticated visitors are redirected to `/login/`.

**Response:** HTML — `profile_page.html`

---

### 6.2 Search API

#### `GET /api/autocomplete`

Returns up to 8 autocomplete phrase suggestions for the authenticated user's corpus as they type. Sets a CSRF cookie on response.

**Authentication:** `Authorization: Token <token>` header required. Returns an empty suggestions list if the token is missing or invalid (no `401` — safe to call while typing).

**Query Parameters:**

| Parameter | Type   | Required | Description          |
|-----------|--------|----------|----------------------|
| `q`       | string | ❌        | Partial search query |

**Search strategy (Trie-backed prefix matching):**

1. Build a user-scoped Trie from cleaned filename phrases (higher weight) and indexed `DocumentPhrase` content (secondary weight).
2. Normalize the query and traverse the Trie by prefix.
3. Return top-k ranked phrase suggestions (deduplicated).

**Response:** `200 OK`

```json
{
  "suggestions": [
    { "phrase": "machine learning notes" },
    { "phrase": "machine learning from first principles" }
  ],
  "csrf_token": "<csrf_token>"
}
```

> Frontend uses the selected `phrase` as the next search query.
```

---

#### `POST /api/search`

Searches the authenticated user's indexed documents and returns results ranked by TF-IDF score.
Returns an empty list with a human-readable message when no documents match or none have been uploaded.

**Authentication:** `Authorization: Token <token>` header required. Returns `401` if missing or invalid.

**Request Body:** `application/json`

| Field   | Type   | Required | Description      |
|---------|--------|----------|------------------|
| `query` | string | ✅        | The search query |

**Example Request:**
```json
{ "query": "machine learning" }
```

**Response:** `200 OK` — results found

```json
{
  "csrf_token": "<csrf_token>",
  "count": 2,
  "results": [
    {
      "file_id": 3,
      "original_filename": "research_paper.pdf",
      "file_type": "pdf",
      "file_url": "http://localhost:8000/media/uploads/2026/03/12/research_paper.pdf",
      "score": 0.847,
      "matched_terms": ["machin", "learn"]
    },
    {
      "file_id": 7,
      "original_filename": "notes.md",
      "file_type": "md",
      "file_url": "http://localhost:8000/media/uploads/2026/03/01/notes.md",
      "score": 0.312,
      "matched_terms": ["machin"]
    }
  ]
}
```

> **Note:** `score` is present in the API response but is not displayed in the UI. Each result filename links directly to the file (opens in a new tab via `file_url`).
```

**Response:** `200 OK` — no matches

```json
{
  "csrf_token": "<csrf_token>",
  "results": [],
  "message": "No matching documents found.",
  "count": 0
}
```

**Error Responses:**

| Status | Condition |
|---|---|
| `400 Bad Request` | Missing or empty `query` field, or invalid JSON |
| `401 Unauthorized` | Missing or invalid `Authorization` token |

> **Note:** Terms in `matched_terms` are Porter-stemmed (e.g. `"learning"` → `"learn"`). Results are scoped strictly to the authenticated user's own files.

---

### 6.3 Authentication API

Base path: `/api/auth/`

---

#### `POST /api/auth/register/`

Registers a new user account and issues an authentication token.

**Permission:** Public (no authentication required)

**Request Body:** `application/json`

| Field              | Type   | Required | Description                            |
|--------------------|--------|----------|----------------------------------------|
| `username`         | string | ✅        | Unique username                        |
| `email`            | string | ✅        | Valid, unique email address            |
| `password`         | string | ✅        | Must pass Django's password validators |
| `password_confirm` | string | ✅        | Must match `password`                  |
| `first_name`       | string | ❌        | User's first name                      |
| `last_name`        | string | ❌        | User's last name                       |

**Example Request:**
```json
{
  "username": "fardin",
  "email": "fardin@example.com",
  "password": "SecurePass123!",
  "password_confirm": "SecurePass123!",
  "first_name": "Fardin",
  "last_name": "Ahmed"
}
```

**Response:** `201 Created`

```json
{
  "user": {
    "id": 1,
    "username": "fardin",
    "email": "fardin@example.com",
    "first_name": "Fardin",
    "last_name": "Ahmed"
  },
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
  "message": "Registration successful. You can now log in."
}
```

**Error Response:** `400 Bad Request`

```json
{
  "errors": { "email": ["A user with this email already exists."] },
  "message": "Registration failed. Please check the provided data."
}
```

**Validation Rules:**
- `password` and `password_confirm` must match
- Email must pass RFC-format regex validation
- Email must be unique across all users
- Password must pass Django's built-in validators (similarity, minimum length, common passwords, numeric-only)

---

#### `POST /api/auth/login/`

Authenticates a user and returns (or reuses an existing) token.

**Permission:** Public (no authentication required)

**Request Body:** `application/json`

| Field      | Type   | Required | Description         |
|------------|--------|----------|---------------------|
| `username` | string | ✅        | Registered username |
| `password` | string | ✅        | Account password    |

**Example Request:**
```json
{
  "username": "fardin",
  "password": "SecurePass123!"
}
```

**Response:** `200 OK`

```json
{
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
  "user": {
    "id": 1,
    "username": "fardin",
    "email": "fardin@example.com",
    "first_name": "Fardin",
    "last_name": "Ahmed"
  },
  "message": "Login successful"
}
```

**Error Response:** `400 Bad Request`

```json
{
  "errors": { "non_field_errors": ["Unable to log in with provided credentials."] },
  "message": "Login failed. Please check your credentials."
}
```

---

#### `POST /api/auth/logout/`

Revokes the current user's authentication token.

**Permission:** Authenticated

**Request Headers:**
```
Authorization: Token <your_token_here>
```

**Response:** `200 OK`

```json
{ "message": "Logout successful" }
```

**Error Response:** `400 Bad Request`

```json
{ "error": "No active token found" }
```

---

#### `GET /api/auth/profile/`

Retrieves the authenticated user's profile.

**Permission:** Authenticated

**Response:** `200 OK`

```json
{
  "id": 1,
  "username": "fardin",
  "email": "fardin@example.com",
  "first_name": "Fardin",
  "last_name": "Ahmed"
}
```

---

#### `PUT /api/auth/profile/`

Updates the authenticated user's profile. `id` and `username` are read-only and cannot be changed.

**Permission:** Authenticated

**Request Body:** `application/json`

| Field        | Type   | Required | Description       |
|--------------|--------|----------|-------------------|
| `email`      | string | ❌        | New email address |
| `first_name` | string | ❌        | New first name    |
| `last_name`  | string | ❌        | New last name     |

**Example Request:**
```json
{
  "email": "newemail@example.com",
  "first_name": "Updated",
  "last_name": "Name"
}
```

**Response:** `200 OK` — Returns the updated user object (same shape as GET profile).

---

#### `POST /api/auth/token/refresh/`

Rotates the authenticated user's token: deletes the current token and issues a brand-new one.

**Permission:** Authenticated

**Response:** `200 OK`

```json
{
  "token": "a3f1b2c9e4d5f6a7b8c9d0e1f2a3b4c5d6e7f8a9",
  "user": {
    "id": 1,
    "username": "fardin",
    "email": "fardin@example.com",
    "first_name": "Fardin",
    "last_name": "Ahmed"
  },
  "message": "Token refreshed successfully"
}
```

**Error Response:** `400 Bad Request`

```json
{ "error": "Token refresh failed" }
```

---

### 6.4 Upload API

Base path: `/api/upload/`

All endpoints require authentication (`Authorization: Token <token>`).

---

#### `GET /api/upload/`

Lists all files uploaded by the authenticated user (excludes soft-deleted files).

**Permission:** Authenticated

**Response:** `200 OK`

```json
{
  "files": [
    {
      "id": 1,
      "original_filename": "research_paper.pdf",
      "file_type": "pdf",
      "file_size": 204800,
      "status": "pending",
      "uploaded_by": "fardin",
      "uploaded_at": "2026-02-23T10:30:00Z",
      "updated_at": "2026-02-23T10:30:00Z",
      "file_url": "http://localhost:8000/media/uploads/2026/02/23/research_paper.pdf"
    }
  ],
  "count": 1
}
```

---

#### `POST /api/upload/`

Uploads one or more files in a single request. The request must be `multipart/form-data`.

**Permission:** Authenticated

**Request:** `multipart/form-data`

| Field   | Type       | Required | Description                                    |
|---------|------------|----------|------------------------------------------------|
| `files` | file (×N)  | ✅        | One or more files to upload (field name `files`) |

> For backwards compatibility a single file submitted under the field name `file` is also accepted.

**Constraints:**
- Allowed file types: `pdf`, `docx`, `png`, `jpg` / `jpeg`, `md`, `txt`
- Maximum file size: **20 MB** per file
- Each file is validated individually; valid files are saved even if others fail

**Response:** `201 Created`

```json
{
  "files": [
    {
      "id": 2,
      "original_filename": "notes.md",
      "file_type": "md",
      "file_size": 1024,
      "status": "pending",
      "uploaded_by": "fardin",
      "uploaded_at": "2026-03-12T09:00:00Z",
      "updated_at": "2026-03-12T09:00:00Z",
      "file_url": "http://localhost:8000/media/uploads/2026/03/12/notes.md"
    }
  ],
  "failed": [],
  "count": 1,
  "message": "1 file(s) uploaded successfully."
}
```

**Partial failure response:** `201 Created` (at least one file succeeded)

```json
{
  "files": ["..."],
  "failed": [
    {
      "filename": "bad.exe",
      "errors": { "file": ["File type not allowed. Allowed types: docx, jpg, md, pdf, png, txt."] }
    }
  ],
  "count": 1,
  "message": "1 file(s) uploaded successfully. 1 file(s) failed."
}
```

**Error Response:** `400 Bad Request` (all files failed or no files submitted)

```json
{
  "failed": ["..."],
  "message": "All uploads failed. Please check the files."
}
```

---

#### `GET /api/upload/<id>/`

Retrieves metadata for a single uploaded file owned by the authenticated user.

**Permission:** Authenticated (must be the file owner)

**Path Parameters:**

| Parameter | Type    | Description                          |
|-----------|---------|--------------------------------------|
| `id`      | integer | The primary key of the uploaded file |

**Response:** `200 OK` — Returns the full file object (same shape as items inside `files` array above).

**Error Responses:**

| Status          | Condition                               |
|-----------------|-----------------------------------------|
| `404 Not Found` | File does not exist                     |
| `403 Forbidden` | File exists but belongs to another user |

---

#### `DELETE /api/upload/<id>/`

Soft-deletes a file owned by the authenticated user. The physical file remains on disk; `deleted_at` is set and `status` changes to `"deleted"`. The file no longer appears in list responses.

**Permission:** Authenticated (must be the file owner)

**Path Parameters:**

| Parameter | Type    | Description                          |
|-----------|---------|--------------------------------------|
| `id`      | integer | The primary key of the uploaded file |

**Response:** `200 OK`

```json
{ "message": "File deleted successfully." }
```

**Error Responses:**

| Status          | Condition                               |
|-----------------|-----------------------------------------|
| `404 Not Found` | File does not exist                     |
| `403 Forbidden` | File exists but belongs to another user |

---

#### `PATCH /api/upload/<id>/`

Renames a file owned by the authenticated user. Updates both `original_filename` in the database **and** the actual file on disk (`os.rename`). The `file` field (stored path) is also updated to reflect the new name.

**Permission:** Authenticated (must be the file owner)

**Path Parameters:**

| Parameter | Type    | Description                          |
|-----------|---------|--------------------------------------|
| `id`      | integer | The primary key of the uploaded file |

**Request Body:** `application/json`

| Field               | Type   | Required | Description         |
|---------------------|--------|----------|---------------------|
| `original_filename` | string | ✅        | The new filename    |

**Example Request:**
```json
{ "original_filename": "leadership_hbr_2001.pdf" }
```

**Response:** `200 OK` — Returns the full updated file object.

**Error Responses:**

| Status          | Condition                                                         |
|-----------------|-------------------------------------------------------------------|
| `400 Bad Request` | `original_filename` is empty, or a different file with that name already exists in the same directory |
| `403 Forbidden` | File exists but belongs to another user                           |
| `404 Not Found` | File does not exist                                               |

---

## 7. Data Models

### `UploadedFile` (app: `upload`)

Stores metadata for each user-uploaded file.

| Field               | Type                       | Description                                        |
|---------------------|----------------------------|----------------------------------------------------|
| `id`                | BigAutoField (PK)          | Auto-incrementing primary key                      |
| `file`              | FileField (max_length=500) | Stored at `uploads/YYYY/MM/DD/` under `MEDIA_ROOT` |
| `original_filename` | CharField (255)            | Original filename as submitted                     |
| `file_type`         | CharField (10)             | Canonical file extension (see choices below)       |
| `file_size`         | PositiveIntegerField       | File size in bytes                                 |
| `uploaded_by`       | ForeignKey → `User`        | Owner; cascade-deleted with the user               |
| `uploaded_at`       | DateTimeField              | Auto-set on creation                               |
| `updated_at`        | DateTimeField              | Auto-updated on save                               |
| `deleted_at`        | DateTimeField (nullable)   | Soft-delete timestamp; `null` means active         |
| `status`            | CharField (20)             | Processing status (see choices below)              |

**`file_type` choices:**

| Value  | Label         |
|--------|---------------|
| `pdf`  | PDF           |
| `docx` | Word Document |
| `png`  | PNG Image     |
| `jpg`  | JPEG Image    |
| `md`   | Markdown      |
| `txt`  | Text File     |

**`status` choices:**

| Value       | Label     | Description                 |
|-------------|-----------|-----------------------------|
| `pending`   | Pending   | Uploaded, awaiting indexing |
| `processed` | Processed | Successfully indexed        |
| `failed`    | Failed    | Indexing failed             |
| `deleted`   | Deleted   | Soft-deleted by the user    |

**Default ordering:** `-uploaded_at` (newest first)

---

### `User` (Django built-in)

The project uses Django's default `auth.User` model (no custom model). Key fields used:

| Field          | Description                                              |
|----------------|----------------------------------------------------------|
| `id`           | Auto-incrementing PK                                     |
| `username`     | Unique login identifier                                  |
| `email`        | Email address (validated for uniqueness at registration) |
| `password`     | Hashed password                                          |
| `first_name`   | Optional                                                 |
| `last_name`    | Optional                                                 |
| `is_active`    | Account active flag                                      |
| `is_staff`     | Admin site access                                        |
| `is_superuser` | All permissions granted                                  |

### `Token` (DRF built-in — `rest_framework.authtoken`)

One token per user, managed by `AuthUtils`. Token key is a 40-character hex string.

---

### `InvertedIndex` (app: `indexer`)

Single-table inverted index. One row per `(document, term)` pair.

| Field                | Type                        | Description                                            |
|----------------------|-----------------------------|--------------------------------------------------------|
| `id`                 | BigAutoField (PK)           | Auto-incrementing primary key                          |
| `document`           | ForeignKey → `UploadedFile` | Source document; cascade-deleted with the file         |
| `term`               | CharField (100)             | Normalized (lowercased, stemmed) token                 |
| `term_frequency`     | FloatField                  | TF = occurrences / total terms in document             |
| `document_frequency` | IntegerField                | # of the owner's documents containing this term        |
| `tf_idf`             | FloatField                  | Precomputed TF-IDF score at index time                 |
| `positions`          | JSONField                   | List of 0-based token-offset positions in the document |
| `indexed_at`         | DateTimeField               | Auto-set when the row is written                       |

**Constraints & indexes:**
- Unique on `(document, term)`
- DB index on `term` and on `document`
- Default ordering: `-tf_idf`

**User isolation:** enforced at query time via `document__uploaded_by=user` — no extra column needed.

---

## 8. Frontend

The frontend is a server-rendered multi-page application served directly by Django from the `static/` directory.

### Pages

#### Home Page — `GET /`

- **Template:** `static/home_page.html`
- **Script:** `static/scripts/index.js`
- **Style:** `static/styles/index.css`
- **Libraries:** Bootstrap 5, jQuery slim, Font Awesome

**Behaviour:**
1. Renders a centered search input and a drag-and-drop file upload area below it.
2. As the user types (debounced at **250 ms**), `index.js` calls `GET /api/autocomplete?q=<query>` and renders phrase suggestions from the Trie-backed backend. Selecting one navigates to `/search?q=<phrase>`.
3. Pressing **Enter** or clicking the search button navigates to `/search?q=<query>`.
4. The upload area accepts multiple files via drag-and-drop or the native file picker (`multiple` attribute). All selected files are sent in a single `POST /api/upload/` request. Each file gets an inline status row showing upload progress and the result (✅ queued / ❌ error).
5. A "My Files" link and a "Sign out" button are injected into the top-right corner on page load.

---

#### Search Results Page — `GET /search/`

- **Template:** `static/search_page.html`
- **Script:** `static/scripts/search.js`
- **Style:** `static/styles/search.css`
- **Libraries:** Bootstrap 5, jQuery slim, Font Awesome

**Behaviour:**
1. On page load, reads `?q=` from the URL and immediately fires `POST /api/search` to display initial results.
2. As the user refines the query (debounced at **250 ms**), the autocomplete dropdown calls `GET /api/autocomplete?q=<query>` and shows phrase suggestions; clicking one runs search with that phrase.
3. Pressing **Enter** or clicking the search button fires `POST /api/search` and replaces the results list.
4. The URL `?q=` parameter is updated via `history.replaceState` without a page reload.
5. Each result card displays: the filename (clickable link that opens the file in a new tab), file type badge, and matched terms. The TF-IDF score is returned by the API but not shown in the UI.
6. The CSRF token is read from the page's hidden `csrfmiddlewaretoken` input and sent as `X-CSRFToken` header.
7. A "My Files" link and a "Sign out" button are injected into the top-right corner on page load.

---

#### Profile Page — `GET /profile/me`

- **Template:** `static/profile_page.html`
- **Script:** `static/scripts/profile.js`
- **Style:** `static/styles/profile.css`
- **Libraries:** Bootstrap 5, jQuery slim, Font Awesome

**Behaviour:**
1. On load, `profile.js` checks for a token in `localStorage`; unauthenticated visitors are redirected to `/login/`.
2. Calls `GET /api/upload/` to fetch the user's files and renders them as cards showing: a colour-coded file type icon, the filename (clickable link, opens in a new tab), a status badge (Processed / Pending / Failed), file type, size, and upload date.
3. A stats line beneath the heading shows total file count, indexed count, and pending count.
4. **Upload** — an "Upload Files" button toggles a drag-and-drop panel (same multi-file behaviour as the home page). After a successful upload the file list refreshes automatically.
5. **Rename** — clicking the pencil icon opens a Bootstrap modal pre-filled with the current filename. Saving calls `PATCH /api/upload/<id>/`, which renames both the DB record and the file on disk. The card updates in-place on success.
6. **Delete** — clicking the trash icon opens a confirmation modal. Confirming calls `DELETE /api/upload/<id>/`; the card fades out and the stats line updates.
7. An empty-state illustration is shown when no files exist.

---

## 9. Error Handling

### Global DRF Exception Handler

`apps/authentication/exceptions.custom_exception_handler` wraps all DRF errors into a consistent envelope:

```json
{
  "error": true,
  "message": "<human-readable message>",
  "details": { "<field>": ["<error>"] }
}
```

The `message` field is derived from:
1. `detail` key in the DRF error (e.g., authentication errors)
2. `non_field_errors[0]` (e.g., validation errors)
3. `"An error occurred"` as a fallback

### Upload-Specific Exceptions

| Exception class          | HTTP Status                    | `default_detail`                                      |
|--------------------------|--------------------------------|-------------------------------------------------------|
| `FileTypeNotAllowed`     | `415 Unsupported Media Type`   | "The uploaded file type is not allowed."              |
| `FileSizeExceeded`       | `413 Request Entity Too Large` | "The uploaded file exceeds the maximum allowed size." |
| `FileNotFound`           | `404 Not Found`                | "The requested file was not found."                   |
| `UnauthorizedFileAccess` | `403 Forbidden`                | "You do not have permission to access this file."     |

---

## 10. Deployment

### Docker

The project ships with a `Dockerfile` and `compose.yml` for container-based deployment.

**Services:**

| Service        | Image                   | Port   | Description         |
|----------------|-------------------------|--------|---------------------|
| `lore-backend` | Built from `Dockerfile` | `8000` | Django application  |
| `database`     | `postgres:18-alpine`    | `5432` | PostgreSQL database |

**Dockerfile highlights:**
- Base image: `python:3.13-slim`
- Installs `libpq-dev` and `gcc` for `psycopg2`
- Creates a non-root `appuser` (UID 1000) for security
- Startup command: `python manage.py migrate && python manage.py runserver 0.0.0.0:8000`
- Static files are collected at build time (`collectstatic`)

**Run with Docker Compose:**

```bash
# Copy and fill in environment variables
cp .env.example .env

# Build and start all services
docker compose up --build
```

The application will be available at `http://localhost:8000`.

### Local Development (without Docker)

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your local PostgreSQL credentials

# Run migrations
python manage.py migrate

# Start the development server
python manage.py runserver
```

---

## 12. Testing

Tests are written with Django's `APITestCase` and `APIClient` from DRF.

**Run tests:**

```bash
pytest
# or with coverage
pytest --cov
```

### `AuthenticationAPITestCase` (`apps/upload/tests.py` + `apps/authentication/tests.py`)

| Test                                         | Endpoint                        | Scenario                                                      |
|----------------------------------------------|---------------------------------|---------------------------------------------------------------|
| `test_user_registration`                     | `POST /api/auth/register/`      | Successful registration returns `201` with `token` and `user` |
| `test_user_registration_password_mismatch`   | `POST /api/auth/register/`      | Mismatched passwords return `400`                             |
| `test_user_registration_duplicate_email`     | `POST /api/auth/register/`      | Duplicate email returns `400`                                 |
| `test_user_login`                            | `POST /api/auth/login/`         | Successful login returns `200` with `token` and `user`        |
| `test_user_login_invalid_credentials`        | `POST /api/auth/login/`         | Bad credentials return `400`                                  |
| `test_user_logout`                           | `POST /api/auth/logout/`        | Token is deleted on logout, returns `200`                     |
| `test_user_profile_get`                      | `GET /api/auth/profile/`        | Returns user data for authenticated user                      |
| `test_user_profile_update`                   | `PUT /api/auth/profile/`        | Updates and returns profile fields                            |
| `test_token_refresh`                         | `POST /api/auth/token/refresh/` | Old token deleted, new token issued                           |
| `test_protected_endpoint_without_token`      | `GET /api/auth/profile/`        | Returns `401` when unauthenticated                            |
| `test_protected_endpoint_with_invalid_token` | `GET /api/auth/profile/`        | Returns `401` for invalid token                               |
| `test_txt_file_is_allowed`                   | Upload validation utility       | Confirms `.txt` files are accepted                            |
| `test_exe_file_is_rejected`                  | Upload validation utility       | Confirms unsupported extensions are rejected                  |

### `IndexerTestCase` (`apps/indexer/tests.py`)

| Test                                                  | Area                      | Scenario                                          |
|-------------------------------------------------------|---------------------------|---------------------------------------------------|
| `test_tokenizer_basic`                                | Tokenization              | Stop-words removed, content words retained        |
| `test_tokenizer_with_positions`                       | Token position indexing   | Positional map is generated                       |
| `test_index_stats_empty`                              | Index statistics          | Empty corpus returns zero counts                  |
| `test_extract_text_supports_txt`                      | Text extraction (`txt`)   | Plain text files are extracted for indexing       |
| `test_prefix_trie_returns_ranked_prefix_matches`      | Trie prefix ranking       | Higher-weight prefix matches are returned first   |
| `test_autocomplete_service_uses_trie_prefix_matching` | Autocomplete service      | User suggestions are resolved through Trie        |
| `test_autocomplete_endpoint_returns_phrase_objects`   | Autocomplete API contract | Endpoint returns `suggestions` with `phrase` keys |
