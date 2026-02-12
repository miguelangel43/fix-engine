# backend/Dockerfile
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed for QuickFIX compilation if not using a wheel)
# We add gcc and g++ just in case QuickFIX needs to compile
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend code
COPY . /app/backend

# Copy the shared code (This is a build-time copy, the volume mount will override it later)
# We assume the build context is usually the backend folder, but since we use
# volumes for development, this step is just a fallback for production builds.
# For now, just ensuring the folder exists is enough.
RUN mkdir -p /app/shared

# Set the python path so it can find 'backend' and 'shared'
ENV PYTHONPATH=/app

# Command to run the engine
CMD ["python", "backend/fix_engine.py"]