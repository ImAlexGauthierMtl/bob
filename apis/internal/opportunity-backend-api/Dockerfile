# ── Dev stage (hot-reload for docker-compose) ──
FROM python:3.11-slim AS dev
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY apis/shared/ /app/shared/
COPY apis/internal/opportunity-backend-api/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH="/app"
EXPOSE ${PORT:-9004}

CMD ["sh", "-c", "uvicorn main:app --reload --host 0.0.0.0 --port ${PORT:-9004}"]

# ── Production stage ──
FROM python:3.11-slim AS production
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY apis/internal/opportunity-backend-api/requirements.txt .
ENV PIP_DEFAULT_TIMEOUT=300
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY apis/shared/ ./shared/
COPY apis/internal/opportunity-backend-api/ ./
ENV PYTHONPATH="/app"

EXPOSE ${PORT:-9004}

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-9004}"]
