# Stage 1
# Use Python 3.14 slim image
FROM python:3.14-slim AS builder

# Set work directory
RUN mkdir /app
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies (incl. Pillow build deps for Python 3.14 source build)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
        curl \
        libjpeg-dev \
        zlib1g-dev \
        libwebp-dev \
        libtiff-dev \
        libopenjp2-7-dev \
    && rm -rf /var/lib/apt/lists/* \
    # Installing gunicorn
    && pip install "gunicorn==23.0.0"
RUN pip install --upgrade pip

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2
FROM python:3.14-slim

# Install PostgreSQL client tools (needed for pg_dump in backup command)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -r appuser && \
   mkdir /app && \
   mkdir -p /backups && \
   chown -R appuser /app /backups

# Copy the Python dependencies from the builder stage
COPY --from=builder /usr/local/lib/python3.14/site-packages/ /usr/local/lib/python3.14/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Set work directory
WORKDIR /app

# Copy project files
COPY --chown=appuser:appuser . .

# Make entry file executable
RUN chmod +x /app/entrypoint.prod.sh

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Start the application using Gunicorn
CMD ["/app/entrypoint.prod.sh"]