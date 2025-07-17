import time
from typing import Dict, List, Optional
from loguru import logger
import json
import os
from datetime import datetime, timedelta
import psutil
import threading

class MonitoringSystem:
    def __init__(self):
        self.operation_history: Dict[str, List[Dict]] = {}
        self.metrics_history: List[Dict] = []
        self.is_monitoring = False
        self.monitor_thread = None
        self.metrics_file = "monitoring_metrics.json"
        self.operations_file = "monitoring_operations.json"
        self.metrics_interval = 5  # seconds
        
    def initialize(self):
        """Initialize monitoring system"""
        try:
            # Load history
            if os.path.exists(self.metrics_file):
                with open(self.metrics_file, "r") as f:
                    self.metrics_history = json.load(f)
                    
            if os.path.exists(self.operations_file):
                with open(self.operations_file, "r") as f:
                    self.operation_history = json.load(f)
                    
            logger.info("Monitoring system initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize monitoring system: {str(e)}")
            raise
            
    def start_monitoring(self):
        """Start monitoring system"""
        try:
            if self.is_monitoring:
                return
                
            self.is_monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            
            logger.info("Monitoring system started")
            
        except Exception as e:
            logger.error(f"Failed to start monitoring: {str(e)}")
            raise
            
    def stop_monitoring(self):
        """Stop monitoring system"""
        try:
            self.is_monitoring = False
            if self.monitor_thread:
                self.monitor_thread.join()
                
            self._save_metrics()
            self._save_operations()
            
            logger.info("Monitoring system stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop monitoring: {str(e)}")
            raise
            
    def operation(self, name: str):
        """Context manager for operation monitoring"""
        return OperationMonitor(self, name)
        
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                # Collect metrics
                metrics = self._collect_metrics()
                self.metrics_history.append(metrics)
                
                # Trim history if too long
                if len(self.metrics_history) > 1000:
                    self.metrics_history = self.metrics_history[-1000:]
                    
                # Save metrics periodically
                if len(self.metrics_history) % 10 == 0:
                    self._save_metrics()
                    
                time.sleep(self.metrics_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(1)
                
    def _collect_metrics(self) -> Dict:
        """Collect system metrics"""
        try:
            process = psutil.Process()
            
            return {
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": process.cpu_percent(),
                "memory_percent": process.memory_percent(),
                "memory_info": {
                    "rss": process.memory_info().rss,
                    "vms": process.memory_info().vms
                },
                "threads": process.num_threads(),
                "open_files": len(process.open_files()),
                "connections": len(process.connections())
            }
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {str(e)}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
            
    def _save_metrics(self):
        """Save metrics history to file"""
        try:
            with open(self.metrics_file, "w") as f:
                json.dump(self.metrics_history, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metrics: {str(e)}")
            raise
            
    def _save_operations(self):
        """Save operation history to file"""
        try:
            with open(self.operations_file, "w") as f:
                json.dump(self.operation_history, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save operations: {str(e)}")
            raise
            
    def get_metrics_summary(self) -> Dict:
        """Get metrics summary"""
        try:
            if not self.metrics_history:
                return {
                    "total_metrics": 0,
                    "latest_metrics": None
                }
                
            # Get latest metrics
            latest = self.metrics_history[-1]
            
            # Calculate averages
            cpu_avg = sum(m["cpu_percent"] for m in self.metrics_history) / len(self.metrics_history)
            memory_avg = sum(m["memory_percent"] for m in self.metrics_history) / len(self.metrics_history)
            
            return {
                "total_metrics": len(self.metrics_history),
                "latest_metrics": latest,
                "averages": {
                    "cpu_percent": cpu_avg,
                    "memory_percent": memory_avg
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get metrics summary: {str(e)}")
            raise
            
    def get_operation_summary(self) -> Dict:
        """Get operation summary"""
        try:
            if not self.operation_history:
                return {
                    "total_operations": 0,
                    "operation_types": {}
                }
                
            # Count operation types
            operation_types = {}
            for op_name, history in self.operation_history.items():
                operation_types[op_name] = {
                    "count": len(history),
                    "avg_duration": sum(op["duration"] for op in history) / len(history)
                }
                
            return {
                "total_operations": sum(len(history) for history in self.operation_history.values()),
                "operation_types": operation_types
            }
            
        except Exception as e:
            logger.error(f"Failed to get operation summary: {str(e)}")
            raise
            
    def cleanup(self):
        """Clean up monitoring system"""
        try:
            self.stop_monitoring()
            self.metrics_history = []
            self.operation_history = {}
            logger.info("Monitoring system cleaned up successfully")
        except Exception as e:
            logger.error(f"Failed to cleanup monitoring system: {str(e)}")
            raise

class OperationMonitor:
    def __init__(self, monitoring: MonitoringSystem, name: str):
        self.monitoring = monitoring
        self.name = name
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            # Calculate duration
            duration = time.time() - self.start_time
            
            # Create operation entry
            operation = {
                "timestamp": datetime.now().isoformat(),
                "duration": duration,
                "success": exc_type is None
            }
            
            # Add to history
            if self.name not in self.monitoring.operation_history:
                self.monitoring.operation_history[self.name] = []
                
            self.monitoring.operation_history[self.name].append(operation)
            
            # Trim history if too long
            if len(self.monitoring.operation_history[self.name]) > 1000:
                self.monitoring.operation_history[self.name] = self.monitoring.operation_history[self.name][-1000:]
                
            # Save operations periodically
            if len(self.monitoring.operation_history[self.name]) % 10 == 0:
                self.monitoring._save_operations()
                
        except Exception as e:
            logger.error(f"Failed to record operation: {str(e)}")
            raise 