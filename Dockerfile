# Use Python 3.12 slim image (3.13 not yet compatible with psycopg2-binary)
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=True
ENV APP_HOME=/app
ENV PORT=8080

# Set work directory
WORKDIR $APP_HOME

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . ./

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app $APP_HOME
USER app

# Expose port
EXPOSE $PORT

# Run the application with gunicorn
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 --worker-class gthread app:app
