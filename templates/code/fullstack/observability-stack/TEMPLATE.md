# Template: Observability Stack

> Configuration Prometheus + Grafana + logs structurés.

## Structure

```
deploy/observability/
├── prometheus-config.yml
├── grafana/
│   └── dashboards/api-dashboard.json
└── docker-compose.observability.yml
```

## `prometheus-config.yml`

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'auth-api'
    static_configs:
      - targets: ['auth-api:8001']
    metrics_path: /metrics

  # Ajouter une entrée par API
  # - job_name: '{resource}-backend-api'
  #   static_configs:
  #     - targets: ['{resource}-backend-api:8002']
  #   metrics_path: /metrics
```

## `docker-compose.observability.yml`

```yaml
version: '3.8'
services:
  prometheus:
    image: prom/prometheus:latest
    ports: ["9090:9090"]
    volumes:
      - ./prometheus-config.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus

  grafana:
    image: grafana/grafana:latest
    ports: ["3000:3000"]
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
    volumes:
      - grafana_data:/var/lib/grafana

  loki:
    image: grafana/loki:latest
    ports: ["3100:3100"]

volumes:
  prometheus_data:
  grafana_data:
```

## Pré-requis backend
Chaque API doit inclure `monitoring-observability/` (endpoint `/metrics`).
