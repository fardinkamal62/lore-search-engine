# Pull official base Python image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN mkdir /app
# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy project files
COPY . /app/

# Create directory for SQLite database
RUN mkdir -p /app/data

# Collect static files
RUN python manage.py collectstatic --noinput || true

# Create a non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Migrate database
#RUN python manage.py migrate

# Run the application
#CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0:8000"]
