FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first
COPY pyproject.toml uv.lock .python-version ./

# Copy cached venv if available (ignore errors if it doesn't exist)
RUN if [ -d .venv ]; then cp -r .venv .venv; fi

# Install uv and sync dependencies
RUN pip install --upgrade pip && \
    pip install uv && \
    uv python pin 3.10 && \
    uv sync

# Copy the rest of the app
COPY . .

# Create symlink to fix imports
RUN ln -sf . backend

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
