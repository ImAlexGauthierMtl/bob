{{/*
Expand the name of the chart.
*/}}
{{- define "frontend-chart.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "frontend-chart.fullname" -}}
{{- if .Values.frontend.name }}
{{- .Values.frontend.name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "frontend-chart.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "frontend-chart.labels" -}}
helm.sh/chart: {{ include "frontend-chart.chart" . }}
{{ include "frontend-chart.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "frontend-chart.selectorLabels" -}}
app.kubernetes.io/name: {{ include "frontend-chart.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: frontend
{{- end }}

{{/*
Image pull secret name
*/}}
{{- define "frontend-chart.imagePullSecretName" -}}
{{- if .Values.imagePullSecrets.name }}
{{- .Values.imagePullSecrets.name }}
{{- else }}
{{- printf "%s-registry-secret" (include "frontend-chart.fullname" .) }}
{{- end }}
{{- end }}
