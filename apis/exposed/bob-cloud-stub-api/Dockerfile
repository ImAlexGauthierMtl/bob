# Dev stage for local/CI Bob Cloud stub
FROM python:3.11-slim AS dev
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY apis/shared/ /app/shared/
COPY apis/exposed/bob-cloud-stub-api/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH="/app"
EXPOSE ${PORT:-8010}

CMD ["sh", "-c", "uvicorn main:app --reload --host 0.0.0.0 --port ${PORT:-8010}"]

# Production image exists only so CI can build the target. Runtime still refuses
# stub mode when ENV/ENVIRONMENT is production.
FROM python:3.11-slim AS production
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY apis/exposed/bob-cloud-stub-api/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY apis/shared/ ./shared/
COPY apis/exposed/bob-cloud-stub-api/ ./
ENV PYTHONPATH="/app"
EXPOSE ${PORT:-8010}

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8010}"]
