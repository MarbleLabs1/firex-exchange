"""
Configuration Manager for the P2P Blockchain application.

This module provides functionality to load, validate, access, and modify
configuration settings for the application.
"""

import os
import json
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Union, List, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConfigError(Exception):
    """Exception raised for configuration-related errors."""
    pass

class ConfigManager:
    """
    Manages application configuration with validation and persistence.
    
    This class provides methods to load configuration from JSON files,
    validate the configuration schema, access and modify configuration values,
    and save changes back to the file system.
    
    Attributes:
        config_path (Path): Path to the active configuration file
        config (Dict): The loaded configuration dictionary
        default_config_path (Path): Path to the default configuration file
    """
    
    # Required configuration fields with their types
    REQUIRED_FIELDS = {
        "application": {
            "name": str,
            "version": str,
            "log_level": str,
            "log_file": str
        },
        "network": {
            "bootstrap_peers": list,
            "rendezvous_string": str,
            "tcp_port": int,
            "protocol_id": str,
            "connection_timeout": int,
            "heartbeat_interval": int,
            "reconnect_attempts": int,
            "reconnect_delay": int
        },
        "blockchain": {
            "difficulty": int,
            "mining_reward": float,
            "block_size_limit": int,
            "transaction_fee": float,
            "database": {
                "path": str,
                "backup_interval": int,
                "max_backups": int
            }
        }
    }
    
    def __init__(self, config_path: Union[str, Path], default_config_path: Optional[Union[str, Path]] = None):
        """
        Initialize the ConfigManager with paths to configuration files.
        
        Args:
            config_path: Path to the active configuration file
            default_config_path: Path to the default configuration file
        
        Raises:
            ConfigError: If configuration file cannot be loaded or validated
        """
        self.config_path = Path(config_path)
        self.default_config_path = Path(default_config_path) if default_config_path else Path(os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'config',
            'default_config.json'
        ))
        self.config = {}
        self.load_config()
    
    def load_config(self) -> None:
        """
        Load configuration from file.
        
        Attempts to load the active configuration file, falling back to the default
        if the active configuration doesn't exist or is invalid.
        
        Raises:
            ConfigError: If neither configuration file can be loaded successfully
        """
        try:
            if self.config_path.exists():
                logger.info(f"Loading configuration from {self.config_path}")
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
                self.validate_config()
            else:
                logger.warning(f"Configuration file not found at {self.config_path}")
                self.load_default_config()
        except (json.JSONDecodeError, ConfigError) as e:
            logger.error(f"Error loading configuration: {e}")
            logger.info("Falling back to default configuration")
            self.load_default_config()
    
    def load_default_config(self) -> None:
        """
        Load the default configuration.
        
        Raises:
            ConfigError: If the default configuration file cannot be loaded or is invalid
        """
        if not self.default_config_path.exists():
            raise ConfigError(f"Default configuration file not found at {self.default_config_path}")
        
        try:
            with open(self.default_config_path, 'r') as f:
                self.config = json.load(f)
            self.validate_config()
            
            # Save the default config to the active config path
            self.save_config()
            logger.info(f"Default configuration saved to {self.config_path}")
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid default configuration file: {e}")
    
    def validate_config(self) -> None:
        """
        Validate the configuration structure and types.
        
        Checks that all required fields are present and have the correct types.
        
        Raises:
            ConfigError: If validation fails
        """
        for section, fields in self.REQUIRED_FIELDS.items():
            if section not in self.config:
                raise ConfigError(f"Missing required section: {section}")
            
            self._validate_section(self.config[section], fields, section)
    
    def _validate_section(self, config_section: Dict, required_fields: Dict, path: str) -> None:
        """
        Recursively validate a configuration section.
        
        Args:
            config_section: The configuration section to validate
            required_fields: The required fields with their types
            path: The dot-notation path to the current section
            
        Raises:
            ConfigError: If validation fails
        """
        for field, field_type in required_fields.items():
            if field not in config_section:
                raise ConfigError(f"Missing required field: {path}.{field}")
            
            if isinstance(field_type, dict):
                if not isinstance(config_section[field], dict):
                    raise ConfigError(
                        f"Field {path}.{field} must be a dictionary, got {type(config_section[field]).__name__}"
                    )
                self._validate_section(config_section[field], field_type, f"{path}.{field}")
            elif not isinstance(config_section[field], field_type):
                raise ConfigError(
                    f"Field {path}.{field} must be of type {field_type.__name__}, "
                    f"got {type(config_section[field]).__name__}"
                )
    
    def get(self, path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        
        Args:
            path: Dot-notation path to the configuration value
            default: Default value to return if the path doesn't exist
            
        Returns:
            The configuration value or the default if not found
        """
        parts = path.split('.')
        value = self.config
        
        for part in parts:
            if not isinstance(value, dict) or part not in value:
                return default
            value = value[part]
        
        return value
    
    def set(self, path: str, value: Any) -> None:
        """
        Set a configuration value using dot notation.
        
        Args:
            path: Dot-notation path to the configuration value
            value: The value to set
            
        Raises:
            ConfigError: If the path is invalid
        """
        parts = path.split('.')
        config = self.config
        
        # Navigate to the parent of the target field
        for i, part in enumerate(parts[:-1]):
            if not isinstance(config, dict):
                raise ConfigError(f"Cannot set {path}: {'.'.join(parts[:i])} is not a dictionary")
            
            if part not in config:
                config[part] = {}
            
            config = config[part]
        
        if not isinstance(config, dict):
            raise ConfigError(f"Cannot set {path}: {'.'.join(parts[:-1])} is not a dictionary")
        
        # Set the value
        config[parts[-1]] = value
    
    def save_config(self) -> None:
        """
        Save the current configuration to the config file.
        
        Creates parent directories if they don't exist.
        
        Raises:
            ConfigError: If the configuration cannot be saved
        """
        try:
            # Create parent directories if they don't exist
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            # Write config to file with pretty formatting
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            
            logger.info(f"Configuration saved to {self.config_path}")
        except (OSError, IOError) as e:
            raise ConfigError(f"Failed to save configuration: {e}")
    
    def reset_to_defaults(self) -> None:
        """
        Reset the configuration to default values.
        
        Raises:
            ConfigError: If the default configuration cannot be loaded
        """
        self.load_default_config()
    
    def backup_config(self, backup_path: Optional[Union[str, Path]] = None) -> Path:
        """
        Create a backup of the current configuration.
        
        Args:
            backup_path: Optional path for the backup file
            
        Returns:
            Path to the backup file
            
        Raises:
            ConfigError: If the backup cannot be created
        """
        if not backup_path:
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            backup_path = self.config_path.with_name(f"{self.config_path.stem}_{timestamp}{self.config_path.suffix}")
        else:
            backup_path = Path(backup_path)
        
        try:
            shutil.copy2(self.config_path, backup_path)
            logger.info(f"Configuration backup created at {backup_path}")
            return backup_path
        except (OSError, IOError) as e:
            raise ConfigError(f"Failed to create configuration backup: {e}")
    
    def get_all(self) -> Dict:
        """
        Get the complete configuration dictionary.
        
        Returns:
            A copy of the current configuration
        """
        return self.config.copy()

# Global configuration instance
_config_instance = None

def get_config(config_path: Optional[Union[str, Path]] = None) -> ConfigManager:
    """
    Get the global ConfigManager instance.
    
    Args:
        config_path: Optional path to the configuration file
        
    Returns:
        The global ConfigManager instance
    """
    global _config_instance
    
    if _config_instance is None:
        if config_path is None:
            # Default configuration path is in the user's config directory
            config_dir = os.path.join(
                os.path.expanduser('~'),
                '.p2p_blockchain'
            )
            config_path = os.path.join(config_dir, 'config.json')
        
        _config_instance = ConfigManager(config_path)
    
    return _config_instance

