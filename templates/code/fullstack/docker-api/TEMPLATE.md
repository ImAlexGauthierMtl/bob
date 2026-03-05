# Template: Dockerfile API (Backend)

> Recette pour créer un Dockerfile pour une API FastAPI.

## Fichier à créer

`{API_NAME}/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
ENV PIP_DEFAULT_TIMEOUT=300
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE ${PORT:-8000}

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

## Multi-stage pour production

```dockerfile
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
EXPOSE ${PORT:-8000}
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "${PORT:-8000}", "--workers", "4"]
```

## Règles NON-NÉGOCIABLES

1. `python:3.11-slim` — jamais alpine (problèmes de compilation)
2. requirements.txt copié avant le code pour le layer caching
3. Port configurable via ENV
4. Pas de secrets dans le Dockerfile
