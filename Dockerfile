FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy project source
COPY . .

# Environment — runtime values injected via HF Space secrets
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# HF Spaces standard port
EXPOSE 7860

# Health check: ping the Streamlit UI
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
    CMD curl -f http://localhost:7860/_stcore/health || exit 1

# Default: run the Streamlit dashboard (HF Space web UI)
# To run inference script instead: docker run ... python inference.py
CMD ["streamlit", "run", "app.py", \
     "--server.port=7860", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
