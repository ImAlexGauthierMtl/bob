# Template: Helm Charts K8s

> Charts Helm pour déployer APIs + frontend sur Kubernetes.

## Structure

```
deploy/helm/
├── api-chart/
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
│       ├── deployment.yaml
│       ├── service.yaml
│       ├── hpa.yaml
│       └── configmap.yaml
└── frontend-chart/
    ├── Chart.yaml
    ├── values.yaml
    └── templates/
        ├── deployment.yaml
        └── service.yaml
```

## `api-chart/values.yaml`

```yaml
replicaCount: 2
image:
  repository: registry.example.com/project/auth-api
  tag: latest
  pullPolicy: IfNotPresent
service:
  type: ClusterIP
  port: 8001
resources:
  limits: { cpu: 500m, memory: 512Mi }
  requests: { cpu: 100m, memory: 128Mi }
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPU: 70
env:
  - name: ENVIRONMENT
    value: production
  - name: DATABASE_URL
    valueFrom:
      secretKeyRef: { name: app-secrets, key: database-url }
```

## `api-chart/templates/deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "api.fullname" . }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app: {{ include "api.name" . }}
  template:
    metadata:
      labels:
        app: {{ include "api.name" . }}
    spec:
      containers:
        - name: {{ .Chart.Name }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          ports:
            - containerPort: {{ .Values.service.port }}
          env: {{- toYaml .Values.env | nindent 12 }}
          resources: {{- toYaml .Values.resources | nindent 12 }}
          livenessProbe:
            httpGet: { path: /health/live, port: {{ .Values.service.port }} }
            initialDelaySeconds: 10
          readinessProbe:
            httpGet: { path: /health/ready, port: {{ .Values.service.port }} }
            initialDelaySeconds: 5
```
