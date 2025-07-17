import psutil
import time
from typing import Dict, Any
from dashboard import DashboardAPI
from notifications import NotificationService

class ResourceMonitor:
    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.dashboard = DashboardAPI()
        self.notifier = NotificationService()
        self.thresholds = {
            'cpu_percent': 90,
            'mem_percent': 85,
            'disk_percent': 80
        }

    def collect_metrics(self) -> Dict[str, Any]:
        return {
            'cpu_percent': psutil.cpu_percent(),
            'mem_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent
        }

    def check_thresholds(self, metrics: Dict[str, Any]):
        for metric, value in metrics.items():
            if value &gt;= self.thresholds[metric]:
                self.notifier.send_alert(
                    f"{metric} threshold exceeded: {value}%"
                )

    def start_monitoring(self):
        while True:
            try:
                metrics = self.collect_metrics()
                self.dashboard.publish_metrics(metrics)
                self.check_thresholds(metrics)
            except Exception as e:
                self.notifier.send_alert(f"Monitoring error: {str(e)}")
            
            time.sleep(self.check_interval)

