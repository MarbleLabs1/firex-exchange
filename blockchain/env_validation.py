import os
import logging
from typing import Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

def validate_port(port: int) -&gt; bool:
    if not 1024 &lt;= port &lt;= 65535:
        logger.error(f"Invalid port {port}: Must be between 1024 and 65535")
        return False
    return True

def validate_secrets(secrets: Dict[str, Any]) -&gt; bool:
    required_keys = {"PRIVATE_KEY", "PUBLIC_KEY", "P2P_SECRET"}
    missing = required_keys - secrets.keys()
    if missing:
        logger.error(f"Missing required secrets: {', '.join(missing)}")
        return False
    return True

def validate_environment() -&gt; None:
    """Check all required environment variables and types"""
    env_vars = {
        "NODE_PORT": {"type": int, "validator": validate_port},
        "P2P_PORT": {"type": int, "validator": validate_port},
        "DB_PATH": {"type": str},
        "LOG_LEVEL": {"type": str}
    }

    missing = []
    errors = []
    secrets = {}
    
    for var, config in env_vars.items():
        value = os.getenv(var)
        if value is None:
            missing.append(var)
            continue
            
        try:
            typed_value = config["type"](value)
            if "validator" in config:
                if not config["validator"](typed_value):
                    errors.append(f"Validation failed for {var}={value}")
        except ValueError:
            errors.append(f"Invalid type for {var}: expected {config['type'].__name__}")
            continue
            
        os.environ[var] = str(typed_value)
    
    secrets = {k: os.getenv(k) for k in {"PRIVATE_KEY", "PUBLIC_KEY", "P2P_SECRET"}}
    if not validate_secrets(secrets):
        errors.append("Secret validation failed")

    template_path = Path(".env.template")
    env_path = Path(".env")
    
    if not env_path.exists():
        logger.warning("Creating .env file from template")
        template_content = "\n".join([f"{var}=" for var in env_vars] + list(secrets.keys()))
        template_path.write_text(template_content)
        env_path.touch(mode=0o600)
        
    if missing:
        logger.critical(f"Missing environment variables: {', '.join(missing)}")
        raise ValueError("Environment validation failed")
        
    if errors:
        logger.critical("Environment errors:\n" + "\n".join(errors))
        raise ValueError("Environment validation failed")

