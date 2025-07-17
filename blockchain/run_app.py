#!/usr/bin/env python3
"""
Script to run the Blockchain P2P Network with AI Integration.
This replaces the run.bat file with a Python script.
"""

import os
import subprocess
import sys
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="Run Blockchain P2P Network with AI Integration")
    parser.add_argument("--host", default="127.0.0.1", help="Host IP to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port for the API (default: 8000)")
    parser.add_argument("--workers", type=int, default=2, help="Number of worker processes (default: 2)")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout for keep-alive connections (default: 30)")
    parser.add_argument("--log-config", default="logging.conf", help="Path to logging configuration file (default: logging.conf)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Set environment variables
    if args.debug:
        os.environ["DEBUG"] = "1"
    
    # Construct the command to run uvicorn
    cmd = [
        "uvicorn",
        "main:app",
        "--host", args.host,
        "--port", str(args.port),
        "--workers", str(args.workers),
        "--timeout-keep-alive", str(args.timeout)
    ]
    
    # Add log config if it exists
    if os.path.exists(args.log_config):
        cmd.extend(["--log-config", args.log_config])
    
    # Print the command being executed
    print(f"Running: {' '.join(cmd)}")
    
    try:
        # Execute the command
        process = subprocess.run(cmd, check=True)
        return process.returncode
    except subprocess.CalledProcessError as e:
        print(f"Error running uvicorn: {e}", file=sys.stderr)
        return e.returncode
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
        return 0
    
if __name__ == "__main__":
    sys.exit(main())
