"""Grafana service for Boltz monitoring."""

import json
import os
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests

from boltz_service.config.base import BaseConfig
from boltz_service.monitoring.grafana_config import (LOGGING_DASHBOARD, MODEL_DASHBOARD,
                                           REQUEST_DASHBOARD, SYSTEM_DASHBOARD,
                                           TRACING_DASHBOARD)
from boltz_service.utils.logging import get_logger

logger = get_logger(__name__)

class GrafanaService:
    """Service for managing Grafana dashboards and data sources."""
    
    def __init__(self, config: BaseConfig):
        """Initialize Grafana service.
        
        Parameters
        ----------
        config : BaseConfig
            Service configuration
        """
        self.config = config
        self.base_url = f"http://{config.metrics.grafana_host}:{config.metrics.grafana_port}"
        self.api_key = config.metrics.grafana_api_key
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Default dashboards
        self.dashboards = {
            "system": SYSTEM_DASHBOARD,
            "requests": REQUEST_DASHBOARD,
            "models": MODEL_DASHBOARD,
            "logs": LOGGING_DASHBOARD,
            "traces": TRACING_DASHBOARD
        }
        
    def setup(self):
        """Set up Grafana with required data sources and dashboards."""
        try:
            # Wait for Grafana to be ready
            self._wait_for_grafana()
            
            # Set up data sources
            self._setup_data_sources()
            
            # Create dashboards
            self._setup_dashboards()
            
            logger.info("Grafana setup completed successfully")
        except Exception as e:
            logger.error(f"Failed to set up Grafana: {e}")
            raise
            
    def _wait_for_grafana(self, timeout: int = 60, interval: int = 5):
        """Wait for Grafana to be ready.
        
        Parameters
        ----------
        timeout : int
            Maximum time to wait in seconds
        interval : int
            Time between health checks in seconds
        """
        start_time = time.time()
        while True:
            try:
                response = requests.get(urljoin(self.base_url, "api/health"))
                if response.status_code == 200:
                    logger.info("Grafana is ready")
                    return
            except requests.exceptions.RequestException:
                pass
                
            if time.time() - start_time > timeout:
                raise TimeoutError("Grafana failed to become ready")
                
            time.sleep(interval)
            
    def _setup_data_sources(self):
        """Set up required data sources."""
        # Prometheus data source
        self._create_data_source({
            "name": "Prometheus",
            "type": "prometheus",
            "url": f"http://{self.config.metrics.prometheus_host}:{self.config.metrics.prometheus_port}",
            "access": "proxy",
            "isDefault": True
        })
        
        # Loki data source
        self._create_data_source({
            "name": "Loki",
            "type": "loki",
            "url": f"http://{self.config.metrics.loki_host}:{self.config.metrics.loki_port}",
            "access": "proxy",
            "jsonData": {
                "maxLines": 1000
            }
        })
        
        # Jaeger data source
        self._create_data_source({
            "name": "Jaeger",
            "type": "jaeger",
            "url": f"http://{self.config.metrics.jaeger_host}:{self.config.metrics.jaeger_query_port}",
            "access": "proxy",
            "jsonData": {
                "nodeGraph": {
                    "enabled": True
                }
            }
        })
        
    def _create_data_source(self, data_source: Dict):
        """Create a Grafana data source.
        
        Parameters
        ----------
        data_source : Dict
            Data source configuration
        """
        try:
            response = requests.post(
                urljoin(self.base_url, "api/datasources"),
                headers=self.headers,
                json=data_source
            )
            
            if response.status_code in (200, 409):  # 409 means already exists
                logger.info(f"Data source '{data_source['name']}' configured")
            else:
                logger.error(f"Failed to create data source: {response.text}")
        except Exception as e:
            logger.error(f"Error creating data source: {e}")
            
    def _setup_dashboards(self):
        """Set up predefined dashboards."""
        for name, dashboard in self.dashboards.items():
            try:
                self.create_dashboard(dashboard)
                logger.info(f"Dashboard '{name}' created successfully")
            except Exception as e:
                logger.error(f"Failed to create dashboard '{name}': {e}")
                
    def create_dashboard(self, dashboard: 'GrafanaDashboard'):
        """Create or update a Grafana dashboard.
        
        Parameters
        ----------
        dashboard : GrafanaDashboard
            Dashboard configuration
        """
        try:
            response = requests.post(
                urljoin(self.base_url, "api/dashboards/db"),
                headers=self.headers,
                json=dashboard.to_json()
            )
            
            if response.status_code == 200:
                logger.info(f"Dashboard '{dashboard.title}' created/updated")
            else:
                logger.error(f"Failed to create dashboard: {response.text}")
        except Exception as e:
            logger.error(f"Error creating dashboard: {e}")
            
    def get_dashboard(self, uid: str) -> Optional[Dict]:
        """Get a dashboard by UID.
        
        Parameters
        ----------
        uid : str
            Dashboard UID
            
        Returns
        -------
        Optional[Dict]
            Dashboard configuration if found
        """
        try:
            response = requests.get(
                urljoin(self.base_url, f"api/dashboards/uid/{uid}"),
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Error getting dashboard: {e}")
            
        return None
        
    def delete_dashboard(self, uid: str):
        """Delete a dashboard by UID.
        
        Parameters
        ----------
        uid : str
            Dashboard UID
        """
        try:
            response = requests.delete(
                urljoin(self.base_url, f"api/dashboards/uid/{uid}"),
                headers=self.headers
            )
            
            if response.status_code == 200:
                logger.info(f"Dashboard {uid} deleted")
            else:
                logger.error(f"Failed to delete dashboard: {response.text}")
        except Exception as e:
            logger.error(f"Error deleting dashboard: {e}")
            
    def create_alert_rule(
        self,
        name: str,
        query: str,
        condition: str,
        dashboard_uid: str,
        panel_id: int,
        notification_channel: str
    ):
        """Create a Grafana alert rule.
        
        Parameters
        ----------
        name : str
            Alert rule name
        query : str
            Alert query
        condition : str
            Alert condition
        dashboard_uid : str
            Dashboard UID
        panel_id : int
            Panel ID
        notification_channel : str
            Notification channel ID
        """
        try:
            alert_data = {
                "dashboard": {
                    "uid": dashboard_uid
                },
                "panelId": panel_id,
                "name": name,
                "message": f"Alert: {name}",
                "conditions": [{
                    "type": "query",
                    "query": {"params": [query]},
                    "reducer": {"type": "avg"},
                    "evaluator": {"type": condition}
                }],
                "notifications": [{
                    "uid": notification_channel
                }]
            }
            
            response = requests.post(
                urljoin(self.base_url, "api/alerts"),
                headers=self.headers,
                json=alert_data
            )
            
            if response.status_code == 200:
                logger.info(f"Alert rule '{name}' created")
            else:
                logger.error(f"Failed to create alert rule: {response.text}")
        except Exception as e:
            logger.error(f"Error creating alert rule: {e}")
            
    def create_error_rate_alert(
        self,
        threshold: float = 0.05,
        window: str = "5m"
    ):
        """Create an alert for high error rates.
        
        Parameters
        ----------
        threshold : float
            Error rate threshold (0-1)
        window : str
            Time window for the alert
        """
        query = f"""
        sum(rate(boltz_requests_total{{status="error"}}[{window}])) /
        sum(rate(boltz_requests_total[{window}]))
        """
        
        self.create_alert_rule(
            name="High Error Rate",
            query=query,
            condition=f"gt {threshold}",
            dashboard_uid=self.dashboards["requests"].uid,
            panel_id=3,  # Error Rate panel
            notification_channel=self.config.metrics.grafana_notification_channel
        )
        
    def create_resource_alerts(
        self,
        cpu_threshold: float = 80.0,
        memory_threshold: float = 80.0,
        gpu_threshold: float = 80.0
    ):
        """Create alerts for resource utilization.
        
        Parameters
        ----------
        cpu_threshold : float
            CPU utilization threshold percentage
        memory_threshold : float
            Memory utilization threshold percentage
        gpu_threshold : float
            GPU utilization threshold percentage
        """
        # CPU Alert
        self.create_alert_rule(
            name="High CPU Usage",
            query="boltz_cpu_utilization",
            condition=f"gt {cpu_threshold}",
            dashboard_uid=self.dashboards["system"].uid,
            panel_id=1,
            notification_channel=self.config.metrics.grafana_notification_channel
        )
        
        # Memory Alert
        self.create_alert_rule(
            name="High Memory Usage",
            query="boltz_memory_utilization",
            condition=f"gt {memory_threshold}",
            dashboard_uid=self.dashboards["system"].uid,
            panel_id=2,
            notification_channel=self.config.metrics.grafana_notification_channel
        )
        
        # GPU Alert
        self.create_alert_rule(
            name="High GPU Usage",
            query="boltz_gpu_utilization",
            condition=f"gt {gpu_threshold}",
            dashboard_uid=self.dashboards["system"].uid,
            panel_id=3,
            notification_channel=self.config.metrics.grafana_notification_channel
        )
