#!/usr/bin/env python3
"""
Uvicorn Server Launcher Script.

This script provides a cross-platform way to launch a FastAPI application
using Uvicorn with various configurable parameters and environment settings.

Features:
- Pre-start validation
- Environment configuration with .env support
- Uvicorn server initialization with customizable parameters
- CLI interface with common server options
- Cross-platform support (Windows/UNIX)
- Comprehensive error handling and user feedback
"""

import argparse
import os
import sys
import socket
import signal
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Try to import dotenv, but make it optional
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("run")

def validate_port(port: int) -> bool:
    """
    Validate if the port number is within the valid range.
    
    Args:
        port: The port number to validate
        
    Returns:
        bool: True if the port is valid, False otherwise
    """
    return 0 <= port <= 65535

def is_port_available(host: str, port: int) -> bool:
    """
    Check if the specified port is available for binding.
    
    Args:
        host: The host to check
        port: The port to check
        
    Returns:
        bool: True if the port is available, False if it's in use
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            return True
    except socket.error:
        return False

def validate_environment() -> Dict[str, str]:
    """
    Validate the necessary files and environment for running the application.
    
    Returns:
        Dict[str, str]: Dictionary containing validation messages
    """
    messages = {}
    
    # Check for main.py
    if not Path("main.py").exists():
        messages["main.py"] = "❌ main.py not found, application cannot start"
    else:
        messages["main.py"] = "✅ main.py found"
    
    # Check for logging.conf
    if not Path("logging.conf").exists():
        messages["logging.conf"] = "⚠️ logging.conf not found, using default logging"
    else:
        messages["logging.conf"] = "✅ logging.conf found"
    
    return messages

def load_environment_variables(env_file: Optional[str] = None) -> None:
    """
    Load environment variables from .env file if available.
    
    Args:
        env_file: Path to the .env file (optional)
    """
    # Always set DEBUG=1 for development environment
    os.environ["DEBUG"] = "1"
    
    # Try to load from .env file if dotenv is available
    if DOTENV_AVAILABLE:
        if env_file and Path(env_file).exists():
            load_dotenv(env_file)
            logger.info(f"🔄 Loaded environment from {env_file}")
        elif Path(".env").exists():
            load_dotenv()
            logger.info("🔄 Loaded environment from .env file")
        else:
            logger.info("ℹ️ No .env file found, using system environment")
    else:
        logger.info("ℹ️ python-dotenv not installed, using system environment only")

def setup_signal_handlers():
    """Set up signal handlers for graceful shutdown on different platforms."""
    def handle_exit_signal(signum, frame):
        """
        Handle exit signals by performing cleanup and exiting gracefully.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info(f"🛑 Received signal {signum}, shutting down...")
        sys.exit(0)
    
    # Set up handlers for common signals
    if sys.platform != "win32":
        # UNIX-like systems
        signal.signal(signal.SIGTERM, handle_exit_signal)
        signal.signal(signal.SIGINT, handle_exit_signal)
    else:
        # Windows only supports SIGINT (CTRL+C)
        signal.signal(signal.SIGINT, handle_exit_signal)

def is_running_as_windows_service() -> bool:
    """
    Detect if the script is running as a Windows service.
    
    Returns:
        bool: True if running as a Windows service, False otherwise
    """
    if sys.platform != "win32":
        return False
        
    try:
        import win32service
        import win32serviceutil
        # This will raise an exception if not run as a service
        service_args = win32serviceutil.HandleCommandLine(None)
        return True
    except (ImportError, TypeError, AttributeError):
        return False
    
def normalize_path(path: str) -> str:
    """
    Normalize a path for the current platform.
    
    Args:
        path: The path to normalize
        
    Returns:
        str: The normalized path
    """
    return str(Path(path).resolve())

def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Run the FastAPI application with Uvicorn server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "--host", 
        default="127.0.0.1", 
        help="Bind socket to this host"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000, 
        help="Bind socket to this port"
    )
    parser.add_argument(
        "--workers", 
        type=int, 
        default=2, 
        help="Number of worker processes"
    )
    parser.add_argument(
        "--keep-alive", 
        type=int, 
        dest="timeout_keep_alive", 
        default=30, 
        help="Keep-alive timeout"
    )
    parser.add_argument(
        "--log-config", 
        dest="log_config", 
        default="logging.conf", 
        help="Path to logging configuration file"
    )
    parser.add_argument(
        "--no-debug",
        action="store_true",
        help="Disable DEBUG mode"
    )
    parser.add_argument(
        "--env-file",
        help="Path to .env file"
    )
    
    return parser.parse_args()

def run_server(app_module: str, **kwargs: Any) -> None:
    """
    Run the Uvicorn server with the specified parameters.
    
    Args:
        app_module: The Python module path to the app
        **kwargs: Additional arguments to pass to uvicorn.run()
    """
    import uvicorn
    
    # Extract and set up parameters
    host = kwargs.pop("host", "127.0.0.1")
    port = kwargs.pop("port", 8000)
    workers = kwargs.pop("workers", 2)
    debug = not kwargs.pop("no_debug", False)
    log_config = kwargs.pop("log_config", "logging.conf")
    
    # Print status messages
    print(f"🚀 Starting server on {host}:{port}")
    print(f"🔧 DEBUG mode {'ENABLED' if debug else 'DISABLED'}")
    print(f"📝 Using log config: {log_config}")
    
    # If running as a service or in production, set debug accordingly
    if is_running_as_windows_service():
        print("🔔 Running as Windows service")
        debug = False
    
    if not debug:
        os.environ["DEBUG"] = "0"
    
    try:
        uvicorn.run(
            app_module,
            host=host,
            port=port,
            workers=workers,
            log_config=log_config if Path(log_config).exists() else None,
            **kwargs
        )
    except Exception as e:
        logger.error(f"❌ Failed to start server: {str(e)}")
        sys.exit(1)

def main() -> None:
    """Main entry point for the application launcher."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Set up signal handlers for graceful shutdown
    setup_signal_handlers()
    
    # Validate port number
    if not validate_port(args.port):
        logger.error(f"❌ Invalid port number: {args.port}. Must be between 0 and 65535.")
        sys.exit(1)
    
    # Check if port is available
    if not is_port_available(args.host, args.port):
        logger.error(f"❌ Port {args.port} is already in use on {args.host}")
        # Suggest alternative ports
        for alternative_port in [args.port + 1, args.port + 2, 8080, 8888]:
            if validate_port(alternative_port) and is_port_available(args.host, alternative_port):
                logger.info(f"💡 Try using port {alternative_port} instead")
                break
        sys.exit(1)
    
    # Load environment variables
    load_environment_variables(args.env_file)
    
    # Validate environment
    validation_messages = validate_environment()
    for key, message in validation_messages.items():
        logger.info(message)
        if message.startswith("❌"):
            sys.exit(1)
    
    # Normalize log_config path
    args.log_config = normalize_path(args.log_config)
    
    # Convert args to dictionary for unpacking
    server_args = vars(args)
    
    # Run the server
    run_server("main:app", **server_args)

if __name__ == "__main__":
    main()

