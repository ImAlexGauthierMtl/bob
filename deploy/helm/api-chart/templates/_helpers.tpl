{{/*
Expand the name of the chart.
*/}}
{{- define "api-chart.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "api-chart.fullname" -}}
{{- if .Values.api.name }}
{{- .Values.api.name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "api-chart.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "api-chart.labels" -}}
helm.sh/chart: {{ include "api-chart.chart" . }}
{{ include "api-chart.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "api-chart.selectorLabels" -}}
app.kubernetes.io/name: {{ include "api-chart.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- if .Values.api.name }}
app.kubernetes.io/component: {{ .Values.api.name }}
{{- end }}
{{- end }}

{{/*
ConfigMap name
*/}}
{{- define "api-chart.configmapName" -}}
{{- if .Values.configMap.name }}
{{- .Values.configMap.name }}
{{- else }}
{{- printf "%s-config" (include "api-chart.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Secret name
*/}}
{{- define "api-chart.secretName" -}}
{{- if .Values.secrets.name }}
{{- .Values.secrets.name }}
{{- else }}
{{- printf "%s-secrets" (include "api-chart.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Image pull secret name
*/}}
{{- define "api-chart.imagePullSecretName" -}}
{{- if .Values.imagePullSecrets.name }}
{{- .Values.imagePullSecrets.name }}
{{- else }}
{{- printf "%s-registry-secret" (include "api-chart.fullname" .) }}
{{- end }}
{{- end }}
