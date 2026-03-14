FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY ../shared /app/shared
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/shared/requirements.txt

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH="/app:/app/.."

EXPOSE ${PORT:-8002}

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8002}"]
