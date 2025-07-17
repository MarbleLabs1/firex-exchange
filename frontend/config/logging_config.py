from pathlib import Path

# Logging paths
LOGS_DIR = Path("logs")
APP_LOG = LOGS_DIR / "app.log"
ERROR_LOG = LOGS_DIR / "error.log"
PERFORMANCE_LOG = LOGS_DIR / "performance.log"
SECURITY_LOG = LOGS_DIR / "security.log"

# Log rotation settings
ROTATION_SIZE = "10 MB"
ROTATION_TIME = "1 day"
RETENTION_DAYS = {
    "app": 7,
    "error": 30,
    "performance": 7,
    "security": 30
}

# Log levels
LOG_LEVELS = {
    "console": "INFO",
    "app": "DEBUG",
    "error": "ERROR",
    "performance": "INFO",
    "security": "INFO"
}

# Log formats
LOG_FORMATS = {
    "console": "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    "file": "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    "performance": "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    "security": "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
}

# Performance logging thresholds (in seconds)
PERFORMANCE_THRESHOLDS = {
    "warning": 1.0,  # Warning if operation takes more than 1 second
    "error": 5.0     # Error if operation takes more than 5 seconds
}

# Security logging categories
SECURITY_CATEGORIES = {
    "AUTH": "Authentication",
    "TRADE": "Trading",
    "WALLET": "Wallet",
    "API": "API Access",
    "SYSTEM": "System"
}

# Log compression settings
COMPRESSION = "zip"

# Log filters
def performance_filter(record):
    return "performance" in record["extra"]

def security_filter(record):
    return "security" in record["extra"]

LOG_FILTERS = {
    "performance": performance_filter,
    "security": security_filter
} 