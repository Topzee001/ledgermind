# Use a lightweight Python base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
# Ensure the /app directory is in the PYTHONPATH so 'import shared' works
ENV PYTHONPATH="/app"

WORKDIR /app

# Install system dependencies (needed for Postgres/build tools)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Add shared module first (for caching)
COPY shared /app/shared

# Accept build-arg for the service to build
ARG SERVICE_NAME
WORKDIR /app/${SERVICE_NAME}

# Copy and install service-specific requirements
COPY ${SERVICE_NAME}/requirements.txt /app/${SERVICE_NAME}/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the service source code
COPY ${SERVICE_NAME} /app/${SERVICE_NAME}

# Default port (will be overridden by Docker Compose mapped ports)
EXPOSE 8000

# By default, use django runserver. For production, you'd use gunicorn.
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
