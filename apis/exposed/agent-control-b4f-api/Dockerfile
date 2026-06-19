# Agent Control B4F deployable.

FROM python:3.11-slim AS dev
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY apis/shared/ /app/shared/
COPY apis/exposed/agent-control-b4f-api/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY apis/exposed/agent-control-b4f-api/app ./app
COPY apis/exposed/agent-control-b4f-api/main.py ./main.py
COPY apis/exposed/agent-control-b4f-api/agent_control_b4f_api ./agent_control_b4f_api

RUN addgroup --system app && adduser --system --ingroup app app && \
    chown -R app:app /app

ENV PYTHONPATH="/app"
ENV CDE_B4F_SURFACE="agent-control"
ENV API_NAME="agent-control-b4f-api"
ENV OTEL_SERVICE_NAME="agent-control-b4f-api"
EXPOSE ${PORT:-8008}
USER app

CMD ["sh", "-c", "uvicorn main:app --reload --host 0.0.0.0 --port ${PORT:-8008}"]

FROM python:3.11-slim AS production
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY apis/exposed/agent-control-b4f-api/requirements.txt .
ENV PIP_DEFAULT_TIMEOUT=300
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY apis/shared/ ./shared/
COPY apis/exposed/agent-control-b4f-api/app ./app
COPY apis/exposed/agent-control-b4f-api/main.py ./main.py
COPY apis/exposed/agent-control-b4f-api/agent_control_b4f_api ./agent_control_b4f_api

RUN addgroup --system app && adduser --system --ingroup app app && \
    chown -R app:app /app

ENV PYTHONPATH="/app"
ENV CDE_B4F_SURFACE="agent-control"
ENV API_NAME="agent-control-b4f-api"
ENV OTEL_SERVICE_NAME="agent-control-b4f-api"
EXPOSE ${PORT:-8008}
USER app

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8008}"]
