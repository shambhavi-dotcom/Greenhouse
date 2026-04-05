"""
Dockerfile

Container configuration for greenhouse environment.
Allows reproducible environment setup and deployment.
"""

FROM python:3.11-slim

WORKDIR /greenhouse

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/greenhouse

# Default command: run inference
CMD ["python", "inference.py"]
