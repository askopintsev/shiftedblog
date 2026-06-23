# Stage 0: Editor UI build
FROM node:22-bookworm AS editor-ui-builder
WORKDIR /editor-ui
COPY editor-ui/package.json editor-ui/package-lock.json* ./
RUN npm ci || npm install
COPY editor-ui/ ./
RUN npm run build

# Keep PYTHON_VERSION in sync with CI (.github/workflows/deploy.yml) and pyproject.toml.
ARG PYTHON_VERSION=3.14

# Stage 1
# Debian Bookworm (stable) — reliable mirrors vs. default slim on newer Debian (e.g. trixie).
FROM python:${PYTHON_VERSION}-slim-bookworm AS builder

ARG PYTHON_VERSION

# Set work directory
RUN mkdir /app
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies (Pillow / psycopg2 / cffi build)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
        libffi-dev \
        curl \
        libjpeg-dev \
        zlib1g-dev \
        libwebp-dev \
        libtiff-dev \
        libopenjp2-7-dev \
        libavif-dev \
    && rm -rf /var/lib/apt/lists/* \
    # Installing gunicorn
    && pip install "gunicorn==23.0.0"
RUN pip install --upgrade pip

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2
FROM python:${PYTHON_VERSION}-slim-bookworm

ARG PYTHON_VERSION

# PostgreSQL client + runtime libs for Pillow (PIL/django_ckeditor_5)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        libffi8 \
        libjpeg62-turbo \
        zlib1g \
        libwebp7 \
        libwebpmux3 \
        libtiff6 \
        libopenjp2-7 \
        libavif15 \
    && rm -rf /var/lib/apt/lists/* \
    && ldconfig

# UID 1000 matches typical VPS deploy users so bind-mounted ./logs is writable.
RUN groupadd -g 1000 appuser && \
    useradd -m -u 1000 -g appuser -s /bin/bash appuser && \
    mkdir /app && \
    mkdir -p /backups && \
    chown -R appuser:appuser /app /backups

# Copy the Python dependencies from the builder stage (PYTHON_VERSION must match FROM above).
COPY --from=builder /usr/local/lib/python${PYTHON_VERSION}/site-packages/ /usr/local/lib/python${PYTHON_VERSION}/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Set work directory
WORKDIR /app

# Ensure loader finds Pillow's libjpeg (libjpeg.so.62)
ENV LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu

# Copy project files
COPY --chown=appuser:appuser . .
COPY --from=editor-ui-builder --chown=appuser:appuser /editor-ui/dist /editor-ui/dist

# Make entry file executable
RUN chmod +x /app/entrypoint.prod.sh

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Entrypoint runs as root to fix bind-mount permissions, then drops to appuser.
USER root

# Expose port
EXPOSE 8000

# Start the application using Gunicorn
CMD ["/app/entrypoint.prod.sh"]
