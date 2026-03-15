FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY contact~backend-api/requirements.txt .
ENV PIP_DEFAULT_TIMEOUT=300
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY contact~backend-api/ ./

ENV PYTHONPATH="/app"

EXPOSE ${PORT:-9002}

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-9002}"]
