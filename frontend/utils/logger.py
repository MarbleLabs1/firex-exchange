import sys
import os
from loguru import logger
import json
from datetime import datetime
from ..config.logging_config import (
    LOGS_DIR, APP_LOG, ERROR_LOG, PERFORMANCE_LOG, SECURITY_LOG,
    ROTATION_SIZE, ROTATION_TIME, RETENTION_DAYS, LOG_LEVELS,
    LOG_FORMATS, PERFORMANCE_THRESHOLDS, SECURITY_CATEGORIES,
    COMPRESSION, LOG_FILTERS
)

def setup_logger():
    """Setup logging configuration"""
    try:
        # Create logs directory if it doesn't exist
        if not os.path.exists(LOGS_DIR):
            os.makedirs(LOGS_DIR)
            
        # Remove default logger
        logger.remove()
        
        # Add console logger
        logger.add(
            sys.stderr,
            format=LOG_FORMATS["console"],
            level=LOG_LEVELS["console"]
        )
        
        # Add file logger for all levels
        logger.add(
            str(APP_LOG),
            rotation=ROTATION_SIZE,
            retention=f"{RETENTION_DAYS['app']} days",
            compression=COMPRESSION,
            format=LOG_FORMATS["file"],
            level=LOG_LEVELS["app"]
        )
        
        # Add file logger for errors only
        logger.add(
            str(ERROR_LOG),
            rotation=ROTATION_SIZE,
            retention=f"{RETENTION_DAYS['error']} days",
            compression=COMPRESSION,
            format=LOG_FORMATS["file"],
            level=LOG_LEVELS["error"]
        )
        
        # Add file logger for performance metrics
        logger.add(
            str(PERFORMANCE_LOG),
            rotation=ROTATION_SIZE,
            retention=f"{RETENTION_DAYS['performance']} days",
            compression=COMPRESSION,
            format=LOG_FORMATS["performance"],
            level=LOG_LEVELS["performance"],
            filter=LOG_FILTERS["performance"]
        )
        
        # Add file logger for security events
        logger.add(
            str(SECURITY_LOG),
            rotation=ROTATION_SIZE,
            retention=f"{RETENTION_DAYS['security']} days",
            compression=COMPRESSION,
            format=LOG_FORMATS["security"],
            level=LOG_LEVELS["security"],
            filter=LOG_FILTERS["security"]
        )
        
        logger.info("Logger initialized successfully")
        
    except Exception as e:
        print(f"Failed to setup logger: {str(e)}")
        raise

def log_performance(operation: str, duration: float, success: bool = True):
    """Log performance metrics"""
    try:
        # Check thresholds and adjust log level
        level = "INFO"
        if duration > PERFORMANCE_THRESHOLDS["error"]:
            level = "ERROR"
        elif duration > PERFORMANCE_THRESHOLDS["warning"]:
            level = "WARNING"
            
        logger.bind(performance=True).log(
            level,
            f"Performance | {operation} | Duration: {duration:.3f}s | Success: {success}"
        )
    except Exception as e:
        logger.error(f"Failed to log performance: {str(e)}")

def log_security(event: str, category: str, details: dict = None):
    """Log security events"""
    try:
        if category not in SECURITY_CATEGORIES:
            category = "SYSTEM"
            
        message = f"Security | {SECURITY_CATEGORIES[category]} | {event}"
        if details:
            message += f" | Details: {json.dumps(details)}"
            
        logger.bind(security=True).info(message)
    except Exception as e:
        logger.error(f"Failed to log security event: {str(e)}")

def get_log_summary() -> dict:
    """Get log summary statistics"""
    try:
        summary = {
            "timestamp": datetime.now().isoformat(),
            "log_files": {},
            "total_entries": 0
        }
        
        # Check each log file
        for log_file in [APP_LOG, ERROR_LOG, PERFORMANCE_LOG, SECURITY_LOG]:
            if os.path.exists(log_file):
                # Count lines
                with open(log_file, "r") as f:
                    line_count = sum(1 for _ in f)
                    
                # Get file size
                file_size = os.path.getsize(log_file)
                
                summary["log_files"][log_file.name] = {
                    "entries": line_count,
                    "size_bytes": file_size
                }
                
                summary["total_entries"] += line_count
                
        return summary
        
    except Exception as e:
        logger.error(f"Failed to get log summary: {str(e)}")
        return {
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        } 