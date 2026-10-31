# ==============================================================================
# EXP-9: Containerization with Docker
# Multi-stage lightweight Python container for DisasterWatch Dashboard
# ==============================================================================
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application directories and files
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY data/ ./data/
COPY streamlit_dashboard.py ./

# Environment configuration
ENV PYTHONPATH=/app/backend:/app
ENV PYTHONUNBUFFERED=1

# Set working directory to backend
WORKDIR /app/backend

# Expose ports: 8000 (FastAPI Core) and 8501 (Streamlit Analytics)
EXPOSE 8000 8501

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

# Launch uvicorn ASGI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
