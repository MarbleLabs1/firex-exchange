#!/usr/bin/env python3
"""
Main entry point for the Blockchain P2P Network with AI Integration.
This script starts all components and the web dashboard.
"""

import asyncio
import logging
import argparse
import os
import sys
from pathlib import Path
import psutil

from fastapi import FastAPI, Depends
from starlette.responses import JSONResponse
from dashboard import DashboardManager, DashboardConfig

def setup_logging(log_level="INFO"):
    """Setup logging configuration using external config file."""
    import logging.config
    import os
    
    # Use the logging.conf file if it exists
    if os.path.exists('logging.conf'):
        logging.config.fileConfig('logging.conf', disable_existing_loggers=False)
        logging.info("Logging configured from logging.conf")
    else:
        # Fallback to basic configuration if file doesn't exist
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f"Invalid log level: {log_level}")
        
        logging.basicConfig(
            level=numeric_level,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('blockchain_network.log')
            ]
        )
        logging.warning("logging.conf not found, using basic config")

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Blockchain P2P Network with AI Integration")
    
    parser.add_argument("--host", default="0.0.0.0", help="Host IP to bind")
    parser.add_argument("--dashboard-port", type=int, default=8000, help="Port for the web dashboard")
    parser.add_argument("--api-port", type=int, default=8000, help="Port for the API")
    parser.add_argument("--p2p-port", type=int, default=8888, help="Port for P2P network")
    parser.add_argument("--node-id", default="node1", help="Unique ID for this node")
    parser.add_argument("--network", default="devnet", choices=["devnet", "testnet", "mainnet"], 
                       help="Solana network to connect to")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
                       help="Logging level")
    
    return parser.parse_args()

def ensure_directories():
    """Ensure all required directories exist."""
    directories = ["static", "data", "logs"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)

def main():
    """Main function to start the system."""
    args = parse_arguments()
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    ensure_directories()
    
    from env_validation import validate_environment
    validate_environment()
    
    try:
        logger.info("Starting Blockchain P2P Network with AI Integration")
        
        # Create dashboard configuration
        config = DashboardConfig(
            node_id=args.node_id,
            host=args.host,
            api_port=args.api_port,
            p2p_port=args.p2p_port,
            dashboard_port=args.dashboard_port,
            solana_network=args.network
        )
        
        # Create FastAPI app
        app = FastAPI(title="Blockchain Node API")
        
        # Add health check endpoint
        @app.get("/health")
        async def health_check():
            """Health check endpoint for the blockchain node.
            
            Returns:
                JSON response with health status information.
            """
            try:
                # Get memory usage statistics
                memory = psutil.virtual_memory()
                memory_stats = {
                    "total": memory.total,
                    "available": memory.available,
                    "percent_used": memory.percent,
                    "used": memory.used,
                    "free": memory.free
                }
                
                # Get blockchain node status from dashboard
                node_status = dashboard.get_node_status() if hasattr(dashboard, 'get_node_status') else "Unknown"
                
                # Get connected peers count
                peers_count = dashboard.get_peers_count() if hasattr(dashboard, 'get_peers_count') else 0
                
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "healthy",
                        "blockchain_node": node_status,
                        "connected_peers": peers_count,
                        "memory_usage": memory_stats
                    }
                )
            except Exception as e:
                logger.error(f"Health check failed: {str(e)}", exc_info=True)
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "unhealthy",
                        "error": str(e)
                    }
                )
        
        # Create and run dashboard
        dashboard = DashboardManager(config)
        # Add FastAPI app to dashboard if supported
        if hasattr(dashboard, 'add_app'):
            dashboard.add_app(app)
        dashboard.run()
        
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        # Run cleanup in a new event loop
        asyncio.run(dashboard.cleanup_components())
    except Exception as e:
        logger.error(f"Error in main: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

