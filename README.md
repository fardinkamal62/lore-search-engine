# Lore
### Personal Search Engine
<sub>Version 1.3.0-Alpha</sub>

Lore is a personal search engine that indexes and searches through your notes, PDFs and documents with
intelligent ranking. Unlike traditional file search, it builds an internal knowledge graph of your content,
understands semantic connections between documents and ranks results based on both keyword relevance and
document relationships. It's like having your own personal Google for everything you've studied or written.

For CSE 0613-305 | Markup and Scripting Languages Lab

# Tech Stack

- Python
- Django
- PostgreSQL
- Docker

# Features

### Planned

- **Document upload and parsing**: Users can upload various document formats (PDF, DOCX, TXT) which are parsed and stored in the database.
- **Document indexing and search**: The system indexes the content of uploaded documents and allows users to perform keyword and semantic searches.
- **Knowledge graph construction**: The system builds a knowledge graph to understand relationships between documents and concepts.
- **Intelligent ranking**: Search results are ranked based on relevance and relationships in the knowledge graph.
- **Autocomplete and suggestions**: As users type search queries, the system provides autocomplete suggestions based on indexed content.
- **Document similarity and recommendations**: The system can recommend related documents based on content similarity and knowledge graph connections.


# Get Started

- Clone the repository:
  ```bash
  git clone https://github.com/fardinkamal62/lore-search-engine.git
  ```

- Navigate to the project directory:
  ```bash
  cd lore-search-engine
  ```

### 🐳 Quick Start with Docker (Recommended)

The easiest way to run the application:

1. Build the Docker image
```bash
docker build -t lore-search-engine .
```

2. Run the container
```bash
docker run -p 8000:8000 lore-search-engine
```

3. Open http://localhost:8000/api/start/



### Manual Setup (Alternative)

- Create a virtual environment:
  ```bash
  python -m venv .venv
  ```

- Activate the virtual environment:
  - On Windows:
    ```bash
    venv\Scripts\activate
    ```
  - On macOS/Linux:
    ```bash
    source venv/bin/activate
    ```
  
- Install the required dependencies:
  ```bash
  pip install -r requirements.txt
  ```

- Create environment file:
  ```bash
  cp .env.example .env
  # Edit .env with your settings
  ```

- Apply database migrations:
  ```bash
  python manage.py migrate
  ```
  
- Create a superuser to access the admin panel:
  ```bash
  python manage.py createsuperuser
  ```

- Start the development server:
  ```bash
  python manage.py runserver
  ```



### Made with ❤️ by team Lore

- [Fardin Kamal](https://github.com/fardinkamal62) - Architecture, deployment, integration, System Design, Django, API
- [Maheer Alam](https://github.com/MaheerJishan3/) - React, UI/UX, visual editor