FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Build context is project root, so paths include backend/
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./

# Upgrade pip first to ensure 'uv' can be found and installed
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir uv && \
    uv python pin 3.10 && \
    uv sync

COPY backend/ ./backend/
COPY app/ ./app/

# Create symlinks so both app and backend modules work
RUN ln -sf /app/backend /app/app

# Set PYTHONPATH to include both app and backend
ENV PYTHONPATH=/app:/app/backend
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Try backend first (which has the full code), then app
CMD ["sh", "-c", "uv run uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 || uv run uvicorn app.api.main:app --host 0.0.0.0 --port 8000"]
