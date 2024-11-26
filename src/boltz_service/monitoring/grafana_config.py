"""Grafana configuration and dashboard templates."""

import json
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class GrafanaDashboard:
    """Grafana dashboard configuration."""
    
    title: str
    uid: str
    panels: List[Dict]
    datasource: str
    refresh: str = "5s"
    time_from: str = "now-1h"
    time_to: str = "now"
    
    def to_json(self) -> dict:
        """Convert dashboard to Grafana JSON format.
        
        Returns
        -------
        dict
            Dashboard in Grafana JSON format
        """
        return {
            "dashboard": {
                "id": None,
                "uid": self.uid,
                "title": self.title,
                "tags": ["boltz"],
                "timezone": "browser",
                "refresh": self.refresh,
                "schemaVersion": 30,
                "version": 1,
                "time": {
                    "from": self.time_from,
                    "to": self.time_to
                },
                "panels": self.panels
            },
            "folderId": 0,
            "overwrite": True
        }

# System metrics dashboard
SYSTEM_DASHBOARD = GrafanaDashboard(
    title="Boltz System Metrics",
    uid="boltz-system",
    datasource="Prometheus",
    panels=[
        # CPU Usage Panel
        {
            "id": 1,
            "title": "CPU Usage",
            "type": "graph",
            "datasource": "Prometheus",
            "targets": [{
                "expr": "boltz_cpu_utilization",
                "legendFormat": "CPU %"
            }],
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
        },
        # Memory Usage Panel
        {
            "id": 2,
            "title": "Memory Usage",
            "type": "graph",
            "datasource": "Prometheus",
            "targets": [{
                "expr": "boltz_memory_utilization",
                "legendFormat": "Memory %"
            }],
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
        },
        # GPU Utilization Panel
        {
            "id": 3,
            "title": "GPU Utilization",
            "type": "graph",
            "datasource": "Prometheus",
            "targets": [{
                "expr": "boltz_gpu_utilization{device=~'gpu.*'}",
                "legendFormat": "{{device}}"
            }],
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
        },
        # GPU Memory Panel
        {
            "id": 4,
            "title": "GPU Memory",
            "type": "graph",
            "datasource": "Prometheus",
            "targets": [{
                "expr": "boltz_gpu_memory_bytes{device=~'gpu.*'} / 1024 / 1024",
                "legendFormat": "{{device}} MB"
            }],
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
        }
    ]
)

# Request metrics dashboard
REQUEST_DASHBOARD = GrafanaDashboard(
    title="Boltz Request Metrics",
    uid="boltz-requests",
    datasource="Prometheus",
    panels=[
        # Request Rate Panel
        {
            "id": 1,
            "title": "Request Rate",
            "type": "graph",
            "datasource": "Prometheus",
            "targets": [{
                "expr": "rate(boltz_requests_total[5m])",
                "legendFormat": "{{method}} - {{status}}"
            }],
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
        },
        # Request Duration Panel
        {
            "id": 2,
            "title": "Request Duration",
            "type": "graph",
            "datasource": "Prometheus",
            "targets": [{
                "expr": "histogram_quantile(0.95, rate(boltz_request_duration_seconds_bucket[5m]))",
                "legendFormat": "{{method}} p95"
            }],
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
        },
        # Error Rate Panel
        {
            "id": 3,
            "title": "Error Rate",
            "type": "graph",
            "datasource": "Prometheus",
            "targets": [{
                "expr": "rate(boltz_requests_total{status='error'}[5m])",
                "legendFormat": "{{method}}"
            }],
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
        },
        # Success Rate Panel
        {
            "id": 4,
            "title": "Success Rate",
            "type": "graph",
            "datasource": "Prometheus",
            "targets": [{
                "expr": "rate(boltz_requests_total{status='success'}[5m]) / rate(boltz_requests_total[5m])",
                "legendFormat": "{{method}}"
            }],
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
        }
    ]
)

# Model metrics dashboard
MODEL_DASHBOARD = GrafanaDashboard(
    title="Boltz Model Metrics",
    uid="boltz-models",
    datasource="Prometheus",
    panels=[
        # Model Load Time Panel
        {
            "id": 1,
            "title": "Model Load Time",
            "type": "graph",
            "datasource": "Prometheus",
            "targets": [{
                "expr": "histogram_quantile(0.95, rate(boltz_model_load_time_seconds_bucket[5m]))",
                "legendFormat": "{{model_name}} - {{model_version}}"
            }],
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
        },
        # Inference Time Panel
        {
            "id": 2,
            "title": "Inference Time",
            "type": "graph",
            "datasource": "Prometheus",
            "targets": [{
                "expr": "histogram_quantile(0.95, rate(boltz_inference_time_seconds_bucket[5m]))",
                "legendFormat": "{{model_name}} - {{model_version}}"
            }],
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
        },
        # Batch Size Distribution Panel
        {
            "id": 3,
            "title": "Batch Size Distribution",
            "type": "heatmap",
            "datasource": "Prometheus",
            "targets": [{
                "expr": "rate(boltz_batch_size_bucket[5m])",
                "legendFormat": "{{model_name}}"
            }],
            "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
        },
        # Sequence Length Distribution Panel
        {
            "id": 4,
            "title": "Sequence Length Distribution",
            "type": "heatmap",
            "datasource": "Prometheus",
            "targets": [{
                "expr": "rate(boltz_sequence_length_bucket[5m])",
                "legendFormat": "{{model_name}}"
            }],
            "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
        }
    ]
)

# Logging dashboard
LOGGING_DASHBOARD = GrafanaDashboard(
    title="Boltz Logs",
    uid="boltz-logs",
    datasource="Loki",
    panels=[
        # Log Volume Panel
        {
            "id": 1,
            "title": "Log Volume",
            "type": "graph",
            "datasource": "Loki",
            "targets": [{
                "expr": 'sum(count_over_time({job="boltz"}[5m])) by (level)',
                "legendFormat": "{{level}}"
            }],
            "gridPos": {"h": 8, "w": 24, "x": 0, "y": 0}
        },
        # Error Logs Panel
        {
            "id": 2,
            "title": "Error Logs",
            "type": "logs",
            "datasource": "Loki",
            "targets": [{
                "expr": '{job="boltz"} |= "ERROR"',
                "legendFormat": ""
            }],
            "gridPos": {"h": 12, "w": 24, "x": 0, "y": 8}
        }
    ]
)

# Tracing dashboard
TRACING_DASHBOARD = GrafanaDashboard(
    title="Boltz Traces",
    uid="boltz-traces",
    datasource="Jaeger",
    panels=[
        # Service Latency Panel
        {
            "id": 1,
            "title": "Service Latency",
            "type": "graph",
            "datasource": "Jaeger",
            "targets": [{
                "expr": "histogram_quantile(0.95, sum(rate(service_latency_bucket[5m])) by (le))",
                "legendFormat": "p95"
            }],
            "gridPos": {"h": 8, "w": 24, "x": 0, "y": 0}
        },
        # Trace Browser Panel
        {
            "id": 2,
            "title": "Trace Browser",
            "type": "traces",
            "datasource": "Jaeger",
            "targets": [{
                "query": "service.name='boltz'"
            }],
            "gridPos": {"h": 12, "w": 24, "x": 0, "y": 8}
        }
    ]
)
