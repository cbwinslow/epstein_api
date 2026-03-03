FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files (build context is ./app)
COPY pyproject.toml uv.lock .python-version ./

# Upgrade pip first to ensure 'uv' can be found and installed
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir uv && \
    uv python pin 3.10 && \
    uv sync

# Copy the rest of the app
COPY . .

# Create symlink to fix imports (app/backend -> app/)
RUN ln -sf . backend

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
