#!/usr/bin/env python3
"""
Marble Blockchain System Orchestrator

This script initializes and runs all components of the Marble Blockchain system:
1. Marble Blockchain Core
2. Marble CLI
3. Marble DEX with web interface

Usage:
    python run_all.py
"""

import os
import sys
import time
import logging
import asyncio
import threading
import subprocess
import signal
import importlib
import traceback
from logging.config import fileConfig
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    force=True
)
logger = logging.getLogger("MarbleOrchestrator")

# Ensure proper encoding for Windows console
import sys
if sys.platform == 'win32':
    import codecs
    try:
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except AttributeError:
        # If running in an environment where stdout/stderr don't have buffer attribute
        pass

# Set up colorful console output if available
try:
    import colorama
    colorama.init()
    
    # Define colors for status messages
    class Colors:
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        BLUE = '\033[94m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'
except ImportError:
    # Define dummy colors if colorama is not available
    class Colors:
        GREEN = ''
        YELLOW = ''
        RED = ''
        BLUE = ''
        ENDC = ''
        BOLD = ''

# Try to load external logging config if available
try:
    if os.path.exists("logging.conf"):
        fileConfig("logging.conf")
        logger.info("Loaded external logging configuration")
except Exception as e:
    logger.warning(f"Could not load external logging config: {e}")

# Constants
DEX_HOST = "127.0.0.1"
DEX_PORT = 8000
CLI_PORT = 8001
BLOCKCHAIN_PORT = 9090

# Add function to check if a port is in use
def is_port_in_use(port, host='127.0.0.1'):
    """Check if a port is already in use"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except socket.error:
            return True

# Add function to find an available port
def find_available_port(start_port, max_attempts=10):
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        if not is_port_in_use(port):
            return port
    raise RuntimeError(f"Could not find an available port in range {start_port}-{start_port + max_attempts-1}")

def check_required_components():
    """Check if all required files and directories exist"""
    missing_components = []
    
    # Check for run_blockchain.py
    if not os.path.exists("run_blockchain.py"):
        missing_components.append("run_blockchain.py (Blockchain Core)")
    
    # Check for cosmic_cli.py
    if not os.path.exists("cosmic_cli.py"):
        missing_components.append("cosmic_cli.py (CLI Interface)")
    
    # Check for marble_dex_app.py
    if not os.path.exists("marble_dex_app.py"):
        missing_components.append("marble_dex_app.py (DEX Application)")
    
    # Check for templates directory for DEX
    if not os.path.exists("templates"):
        missing_components.append("templates/ directory (DEX Templates)")
    else:
        # Check for index.html or similar in templates
        template_files = os.listdir("templates")
        if not any(f.endswith('.html') for f in template_files):
            missing_components.append("HTML templates in templates/ directory")
            
    # Check for required Python packages
    required_packages = ["uvicorn", "colorama", "matplotlib", "fastapi"]
    for package in required_packages:
        try:
            importlib.import_module(package)
        except ImportError:
            missing_components.append(f"{package} (Python package)")
    
    # Check for static directory
    if not os.path.exists("static"):
        logger.warning("static/ directory not found, it will be created if needed")
    
    if missing_components:
        logger.error(f"Missing required components: {', '.join(missing_components)}")
        return False
    
    return True

# Global flags and events for component status
# Initialize global variables at module level before they're used
blockchain_ready = threading.Event()
blockchain_error = None
blockchain_running = False  # For backward compatibility
cli_running = False
dex_running = False
processes = []
stop_event = threading.Event()
exit_code = 0  # Global exit code
startup_complete = False  # Flag to indicate startup phase is complete
component_startup_in_progress = True  # Flag to indicate components are still starting up
def signal_handler(sig, frame):
    """Handle termination signals by setting stop event"""
    logger.info("Received shutdown signal, stopping all components...")
    stop_event.set()
    
    # If this is during startup phase, don't directly exit
    # Let the main function handle the shutdown
    global startup_complete
    if not startup_complete:
        logger.info("Signal received during startup, deferring exit handling to main function")
        return
        
    # Give processes a chance to shut down gracefully
    shutdown_timeout = 10  # Increased timeout for better graceful shutdown
    shutdown_start = time.time()
    
    # First, send SIGTERM to all processes
    for proc in processes:
        if proc and proc.poll() is None:
            try:
                if sys.platform == 'win32':
                    proc.terminate()
                else:
                    proc.send_signal(signal.SIGTERM)
                logger.info(f"Terminating process PID: {proc.pid}")
            except Exception as e:
                logger.error(f"Error terminating process: {e}")
    
    # Wait for processes to terminate gracefully
    while time.time() - shutdown_start < shutdown_timeout:
        remaining = [p for p in processes if p and p.poll() is None]
        if not remaining:
            logger.info("All processes terminated gracefully")
            break
        logger.info(f"Waiting for {len(remaining)} processes to terminate...")
        time.sleep(1)
    
    # Force kill any remaining processes
    remaining = [p for p in processes if p and p.poll() is None]
    for proc in remaining:
        try:
            if sys.platform == 'win32':
                proc.kill()
            else:
                proc.send_signal(signal.SIGKILL)
            logger.info(f"Force killing process PID: {proc.pid}")
        except Exception as e:
            logger.error(f"Error killing process: {e}")
    
    # Clear the process list after shutdown
    processes.clear()
    
    # Use the global exit code
    global exit_code
    sys.exit(exit_code)

def run_blockchain_core():
    """Start the Marble Blockchain Core component"""
    global blockchain_error, exit_code, blockchain_ready
    
    # Check if blockchain port is available
    blockchain_port = BLOCKCHAIN_PORT
    if is_port_in_use(blockchain_port):
        logger.warning(f"Port {blockchain_port} already in use, finding alternative...")
        try:
            blockchain_port = find_available_port(blockchain_port + 1)
            logger.info(f"Using alternative port {blockchain_port} for blockchain")
        except RuntimeError as e:
            logger.error(f"Cannot start blockchain: {e}")
            return False
    
    try:
        logger.info(f"{Colors.BLUE}Starting Marble Blockchain Core on port {blockchain_port}...{Colors.ENDC}")
        logger.debug("Checking for blockchain executable files...")
        
        # Use subprocess method for better isolation
        env = os.environ.copy()
        env["MARBLE_BLOCKCHAIN_PORT"] = str(blockchain_port)
        
        # Check if run_blockchain.py exists, otherwise use direct import
        if os.path.exists("run_blockchain.py"):
            # Use --rpc-port instead of --port for compatibility with run_blockchain.py
            cmd = [sys.executable, "run_blockchain.py", "--rpc-port", str(blockchain_port)]
            proc = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                env=env
            )
            processes.append(proc)
            logger.info(f"{Colors.GREEN}Started Blockchain Core as process: {proc.pid}{Colors.ENDC}")
            # Don't set ready flag immediately - wait for proper initialization
            blockchain_running = True
            # We'll let check_blockchain_ready set the blockchain_ready flag
            
            # Check for immediate exit
            returncode = proc.poll()
            if returncode is not None:
                logger.error(f"{Colors.RED}Blockchain process exited immediately with code: {returncode}{Colors.ENDC}")
                blockchain_ready.clear()
                blockchain_error = f"Blockchain process exited immediately with code: {returncode}"
                
                # Check process output for error details
                try:
                    stderr_output = proc.stderr.read().decode('utf-8', errors='replace')
                    if stderr_output:
                        logger.error(f"Blockchain stderr: {stderr_output}")
                        blockchain_error = f"{blockchain_error}. Error: {stderr_output}"
                except Exception as e:
                    logger.error(f"Failed to read blockchain stderr: {e}")
                exit_code = 1
                blockchain_running = False
                return False
            
            # Start a thread to pipe output to our logs
            # Start a thread to pipe output to our logs
            def log_output(pipe, level):
                for line in iter(pipe.readline, b''):
                    try:
                        line_str = line.decode('utf-8', errors='replace').strip()
                        if level == logging.INFO:
                            logger.info(f"[Blockchain] {line_str}")
                        else:
                            logger.error(f"[Blockchain] {line_str}")
                    except Exception as e:
                        logger.error(f"Error processing blockchain output: {e}")
                        
            threading.Thread(target=log_output, args=(proc.stdout, logging.INFO), daemon=True).start()
            threading.Thread(target=log_output, args=(proc.stderr, logging.ERROR), daemon=True).start()
            return True
            
        else:
            # Fallback method - try to run the blockchain module directly
            # Try to import blockchain code directly if run_blockchain.py isn't available
            logger.warning(f"{Colors.YELLOW}run_blockchain.py not found, attempting direct module import{Colors.ENDC}")
            try:
                try:
                    from marble_blockchain import MarbleBlockchain
                    blockchain = MarbleBlockchain(port=blockchain_port)
                except Exception as e:
                    logger.error(f"{Colors.RED}Failed to initialize blockchain: {e}{Colors.ENDC}")
                    raise
                
                # Create thread that will run the async startup
                def run_blockchain_async():
                    async def startup():
                        global blockchain_running, blockchain_ready, blockchain_error
                        try:
                            await blockchain.start()
                            # Set the global state
                            blockchain_ready.set()
                            logger.info(f"{Colors.GREEN}Marble Blockchain Core started successfully{Colors.ENDC}")
                            # Keep running until stop signal
                            while not stop_event.is_set():
                                await asyncio.sleep(1)
                                
                            # Cleanup
                            await blockchain.stop()
                            logger.info("Marble Blockchain Core stopped")
                            logger.info("Marble Blockchain Core shutdown complete")
                        except Exception as e:
                            logger.error(f"{Colors.RED}Error in blockchain async function: {e}{Colors.ENDC}")
                            blockchain_error = str(e)
                            blockchain_ready.clear()
                    
                    # Create new event loop for this thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(startup())
                    except Exception as e:
                        logger.error(f"{Colors.RED}Error in blockchain event loop: {e}{Colors.ENDC}")
                        blockchain_error = str(e)
                        blockchain_ready.clear()
                        loop.close()
                
                # Start blockchain in a thread
                blockchain_thread = threading.Thread(target=run_blockchain_async)
                blockchain_thread.daemon = True
                blockchain_thread.start()
                return True
            except ImportError as e:
                logger.error(f"{Colors.RED}Failed to import MarbleBlockchain: {e}{Colors.ENDC}")
                # Try one more fallback approach - run as a module
                try:
                    cmd = [sys.executable, "-m", "blockchain", "--port", str(blockchain_port)]
                    proc = subprocess.Popen(
                        cmd, 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE,
                        env=env
                    )
                    processes.append(proc)
                    logger.info(f"{Colors.GREEN}Started Blockchain Core as module: {proc.pid}{Colors.ENDC}")
                    return True
                except Exception as e2:
                    logger.error(f"{Colors.RED}All blockchain startup methods failed. Last error: {e2}{Colors.ENDC}")
                    return False
    except Exception as e:
        logger.error(f"{Colors.RED}Failed to start Blockchain Core: {e}{Colors.ENDC}")
        logger.error(f"{Colors.RED}Failed to start Blockchain Core: {e}{Colors.ENDC}")
        logger.exception("Blockchain startup exception details:")
        blockchain_error = str(e)
        blockchain_ready.clear()
        exit_code = 1
        return False

def run_cli():
    """Start the Marble CLI interface"""
    global cli_running, exit_code
    
    # Verify cosmic_cli.py exists and is configured correctly
    if not os.path.exists("cosmic_cli.py"):
        logger.error(f"{Colors.RED}cosmic_cli.py not found. Cannot start CLI.{Colors.ENDC}")
        exit_code = 1
        return False
    
    # Check if CLI port is available (if it uses one)
    cli_port = CLI_PORT
    if is_port_in_use(cli_port):
        logger.warning(f"Port {cli_port} already in use, finding alternative...")
        try:
            cli_port = find_available_port(cli_port + 1)
            logger.info(f"Using alternative port {cli_port} for CLI")
        except RuntimeError as e:
            logger.error(f"Cannot start CLI: {e}")
            exit_code = 1
            return False
    
    try:
        logger.info(f"{Colors.BLUE}Starting Marble CLI on port {cli_port}...{Colors.ENDC}")
        
        # Set environment variables for CLI
        env = os.environ.copy()
        env["MARBLE_CLI_PORT"] = str(cli_port)
        env["MARBLE_BLOCKCHAIN_PORT"] = str(BLOCKCHAIN_PORT)
        
        # Run CLI as subprocess
        # Run CLI as subprocess
        cmd = [sys.executable, "cosmic_cli.py", "--port", str(cli_port)]
        proc = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            env=env
        )
        processes.append(proc)
        
        logger.info(f"{Colors.GREEN}Started Marble CLI as process: {proc.pid}{Colors.ENDC}")
        cli_running = True
        # Log initial process status
        initial_status = proc.poll()
        if initial_status is not None:
            logger.error(f"{Colors.RED}CLI process exited immediately with code: {initial_status}{Colors.ENDC}")
            cli_running = False
            exit_code = 1
            return False
        
        # Start a thread to pipe output to our logs
        def log_output(pipe, level):
            for line in iter(pipe.readline, b''):
                try:
                    line_str = line.decode('utf-8', errors='replace').strip()
                    if level == logging.INFO:
                        logger.info(f"[CLI] {line_str}")
                    else:
                        logger.error(f"[CLI] {line_str}")
                except Exception as e:
                    logger.error(f"Error processing CLI output: {e}")
                    
        threading.Thread(target=log_output, args=(proc.stdout, logging.INFO), daemon=True).start()
        threading.Thread(target=log_output, args=(proc.stderr, logging.ERROR), daemon=True).start()
        
        # Monitor CLI process in a thread
        def monitor_cli():
            while not stop_event.is_set():
                returncode = proc.poll()
                if returncode is not None:
                    logger.error(f"{Colors.RED}CLI process exited with code: {returncode}{Colors.ENDC}")
                    global exit_code
                    cli_running = False
                    if returncode != 0 and startup_complete:
                        # Only set exit code if this happens after startup is complete
                        exit_code = 1
                    break
                time.sleep(1)
                
        cli_thread = threading.Thread(target=monitor_cli)
        cli_thread.daemon = True
        cli_thread.start()
        
        return True
        
    except Exception as e:
        logger.error(f"{Colors.RED}Failed to start CLI: {e}{Colors.ENDC}")
        logger.exception("CLI startup exception details:")
        cli_running = False
        exit_code = 1
        return False

def run_dex():
    """Start the Marble DEX with web interface"""
    global dex_running, exit_code
    
    # Verify marble_dex_app.py exists
    if not os.path.exists("marble_dex_app.py"):
        logger.error(f"{Colors.RED}marble_dex_app.py not found. Cannot start DEX.{Colors.ENDC}")
        return False
    
    # Check if templates directory exists
    if not os.path.exists("templates"):
        logger.error(f"{Colors.RED}templates directory not found. Cannot start DEX.{Colors.ENDC}")
        return False
        
    # Check if DEX port is available
    dex_port = DEX_PORT
    if is_port_in_use(dex_port):
        logger.warning(f"Port {dex_port} already in use, finding alternative...")
        try:
            dex_port = find_available_port(dex_port + 1)
            logger.info(f"Using alternative port {dex_port} for DEX")
        except RuntimeError as e:
            logger.error(f"Cannot start DEX: {e}")
            return False
    
    try:
        logger.info(f"{Colors.BLUE}Starting Marble DEX on {DEX_HOST}:{dex_port}...{Colors.ENDC}")
        
        # Run DEX using uvicorn
        cmd = [
            sys.executable, "-m", "uvicorn", 
            "marble_dex_app:app", 
            "--host", DEX_HOST, 
            "--port", str(dex_port)
        ]
        
        env = os.environ.copy()
        env["MARBLE_DEX_PORT"] = str(dex_port)
        env["MARBLE_BLOCKCHAIN_PORT"] = str(BLOCKCHAIN_PORT)
        proc = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            env=env
        )
        processes.append(proc)
        
        logger.info(f"{Colors.GREEN}Started Marble DEX as process: {proc.pid}{Colors.ENDC}")
        dex_running = True
        
        # Check for immediate failures
        initial_status = proc.poll()
        if initial_status is not None:
            logger.error(f"{Colors.RED}DEX process exited immediately with code: {initial_status}{Colors.ENDC}")
            dex_running = False
            exit_code = 1
            return False
        # Start a thread to pipe output to our logs
        def log_output(pipe, level):
            for line in iter(pipe.readline, b''):
                try:
                    line_str = line.decode('utf-8', errors='replace').strip()
                    if level == logging.INFO:
                        logger.info(f"[DEX] {line_str}")
                    else:
                        logger.error(f"[DEX] {line_str}")
                except Exception as e:
                    logger.error(f"Error processing DEX output: {e}")
                    
        threading.Thread(target=log_output, args=(proc.stdout, logging.INFO), daemon=True).start()
        threading.Thread(target=log_output, args=(proc.stderr, logging.ERROR), daemon=True).start()
        
        # Monitor DEX process in a thread
        def monitor_dex():
            while not stop_event.is_set():
                returncode = proc.poll()
                if returncode is not None:
                    logger.error(f"{Colors.RED}DEX process exited with code: {returncode}{Colors.ENDC}")
                    global exit_code
                    dex_running = False
                    if returncode != 0:
                        exit_code = 1
                    break
                time.sleep(1)
                
        dex_thread = threading.Thread(target=monitor_dex)
        dex_thread.daemon = True
        dex_thread.start()
        
        # Check DEX is actually responding
        def check_dex_ready():
            import time
            import requests
            MAX_TRIES = 10
            for i in range(MAX_TRIES):
                try:
                    time.sleep(2)  # Wait for DEX to initialize
                    response = requests.get(f"http://{DEX_HOST}:{dex_port}/")
                    if response.status_code == 200:
                        logger.info(f"{Colors.GREEN}DEX is ready and responding at http://{DEX_HOST}:{dex_port}/{Colors.ENDC}")
                        return True
                except Exception as e:
                    if i < MAX_TRIES - 1:
                        logger.info(f"DEX not ready yet, retrying... ({i+1}/{MAX_TRIES}): {e}")
                    else:
                        logger.warning(f"{Colors.YELLOW}DEX might not be responding properly: {e}{Colors.ENDC}")
            return False
        
        ready_thread = threading.Thread(target=check_dex_ready)
        ready_thread.daemon = True
        ready_thread.start()
        
        return True
        
    except Exception as e:
        logger.error(f"{Colors.RED}Failed to start DEX: {e}{Colors.ENDC}")
        logger.exception("DEX startup exception details:")
        dex_running = False
        exit_code = 1
        return False

def check_blockchain_ready():
    """Check if the blockchain is ready and responding"""
    global blockchain_running, blockchain_error, blockchain_ready, stop_event  # Declare all globals at the beginning of the function
    import time
    import socket
    
    # On Windows, provide more time for startup
    if sys.platform == 'win32':
        MAX_TRIES = 45  # Increased for Windows which might be slower
    else:
        MAX_TRIES = 30  # Default for other platforms
    startup_phase = True  # Don't log too verbosely after first success
    port = BLOCKCHAIN_PORT
    host = "127.0.0.1"
    
    for i in range(MAX_TRIES):
        # First check if the blockchain_ready event is set
        if blockchain_ready.is_set():
            # Also update the flag for backward compatibility
            blockchain_running = True
            logger.info(f"{Colors.GREEN}Blockchain Core is ready according to internal state{Colors.ENDC}")
            return True
            
        # Next check if we can connect to the blockchain port
        try:
            # First try to connect to the port
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex((host, port))
                if result == 0:
                    # If we can connect, set the ready event
                    blockchain_ready.set()
                    blockchain_running = True
                    logger.info(f"{Colors.GREEN}Blockchain Core responding on port {port}{Colors.ENDC}")
                    return True
        except Exception as e:
            pass
            
        # Check if there's been an error
        if blockchain_error:
            logger.error(f"{Colors.RED}Blockchain startup error detected: {blockchain_error}{Colors.ENDC}")
            return False
            
        # Check if stop event is set
        if stop_event.is_set():
            logger.warning("Stop event detected during blockchain readiness check")
            return False
            
        if startup_phase or (i+1) % 5 == 0:  # Log less frequently after initial startup
            logger.info(f"Blockchain not ready yet, retrying... ({i+1}/{MAX_TRIES})")
        time.sleep(1)
        
    logger.error(f"{Colors.RED}Timed out waiting for Blockchain Core to start{Colors.ENDC}")
    return False

def monitor_components():
    """Monitor the status of all components"""
    last_status_message = ""
    failure_counts = {"blockchain": 0, "cli": 0, "dex": 0}
    logger.info("Component monitoring initialized")
    
    # Wait until startup phase is complete before monitoring for failures
    while component_startup_in_progress and not stop_event.is_set():
        time.sleep(1)
        logger.debug("Waiting for startup to complete before monitoring components")
    
    # Main monitoring loop
    while not stop_event.is_set():
        status = []  # Initialize status list
        
        # Use ASCII characters instead of Unicode for better compatibility
        if blockchain_ready.is_set():
            status.append("Blockchain: Running")
        else:
            status.append("Blockchain: Not Running")
            
        if cli_running:
            status.append("CLI: Running")
        else:
            status.append("CLI: Not Running")
            
        if dex_running:
            status.append("DEX: Running")
        else:
            status.append("DEX: Not Running")
            
        status_message = f"System Status: {' | '.join(status)}"
        # Only log if status has changed
        if status_message != last_status_message:
            logger.info(status_message)
            last_status_message = status_message
        
        # In case of critical component failure, attempt restart
        # Only attempt restarts after startup phase is complete
        # In case of critical component failure, attempt restart
        # Only attempt restarts after startup phase is complete
        if not blockchain_ready.is_set() and not stop_event.is_set() and not component_startup_in_progress:
            failure_counts["blockchain"] += 1
            logger.info(f"Blockchain not running, failure count: {failure_counts['blockchain']}")
            if failure_counts["blockchain"] <= 3:  # Only try to restart 3 times
                logger.warning(f"{Colors.YELLOW}Blockchain Core not running (attempt {failure_counts['blockchain']}), attempting to restart...{Colors.ENDC}")
                try:
                    blockchain_thread = threading.Thread(target=run_blockchain_core)
                    blockchain_thread.daemon = True
                    blockchain_thread.start()
                    logger.info(f"Blockchain restart thread started with ID: {blockchain_thread.ident}")
                except Exception as e:
                    logger.error(f"{Colors.RED}Failed to restart blockchain: {e}{Colors.ENDC}")
                    logger.error("Blockchain restart error details: %s", traceback.format_exc())
            else:
                logger.error(f"{Colors.RED}Blockchain Core failed to restart after multiple attempts{Colors.ENDC}")
        else:
            failure_counts["blockchain"] = 0  # Reset counter when working
            logger.debug("Blockchain is running, reset failure counter")
            failure_counts["cli"] = 0  # Reset counter when working
            
        if not dex_running and blockchain_ready.is_set() and not stop_event.is_set() and not component_startup_in_progress:
            failure_counts["dex"] += 1
            if failure_counts["dex"] <= 3:  # Only try to restart 3 times
                logger.warning(f"{Colors.YELLOW}DEX not running (attempt {failure_counts['dex']}), attempting to restart...{Colors.ENDC}")
                dex_thread = threading.Thread(target=run_dex)
                dex_thread.daemon = True
                dex_thread.start()
            else:
                logger.warning(f"{Colors.YELLOW}DEX failed to restart after multiple attempts{Colors.ENDC}")
        else:
            failure_counts["dex"] = 0  # Reset counter when working
            
        time.sleep(30)  # Check status every 30 seconds

def main():
    """Main entry point for the orchestrator"""
    # Initialize global variables
    global exit_code, blockchain_ready, blockchain_running, cli_running, dex_running, startup_complete, component_startup_in_progress
    exit_code = 0
    blockchain_ready.clear()
    blockchain_running = False
    cli_running = False
    dex_running = False
    startup_complete = False
    component_failure_detected = False  # Initialize failure detection flag
    component_startup_in_progress = True  # Set startup phase flag
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        print("Starting Marble Blockchain System...")
        sys.stdout.flush()
        logger.info("Starting Marble Blockchain System Orchestrator...")
        
        # Check if required components are available
        print("Checking required components...")
        sys.stdout.flush()
        if not check_required_components():
            print("Error: Missing required components")
            sys.stdout.flush()
            return
        print("All required components found")
        sys.stdout.flush()
        
        # Create data directories if they don't exist
        data_dir = Path.home() / ".marble"
        data_dir.mkdir(exist_ok=True)
        
        # Start components in separate threads with enhanced error tracking
        print("Starting Blockchain Core...")
        sys.stdout.flush()
        try:
            logger.info("Initializing blockchain thread")
            blockchain_thread = threading.Thread(target=run_blockchain_core)
            blockchain_thread.daemon = True
            blockchain_thread.start()
            print("Blockchain thread started")
            sys.stdout.flush()
            logger.info("Blockchain thread started successfully with ID: %s", blockchain_thread.ident)
        except Exception as e:
            logger.error(f"{Colors.RED}Failed to start blockchain thread: {e}{Colors.ENDC}")
            logger.error("Blockchain startup error details: %s", traceback.format_exc())
            exit_code = 1
            return
        
        # Wait a moment for immediate failures to be detected
        logger.info("Waiting to check for immediate blockchain failures...")
        time.sleep(2)  # Extended wait time to allow for startup errors to propagate
        if exit_code != 0:
            logger.error(f"{Colors.RED}Blockchain startup detected an immediate failure{Colors.ENDC}")
            logger.error(f"Exit code: {exit_code}, Blockchain error: {blockchain_error}")
            sys.exit(exit_code)
        # Wait for blockchain to initialize before starting other components
        logger.info("Waiting for blockchain to initialize...")
        startup_begin_time = time.time()
        try:
            blockchain_is_ready = check_blockchain_ready()
            logger.info(f"Blockchain ready check result: {blockchain_is_ready}")
        except Exception as e:
            logger.error(f"{Colors.RED}Error checking blockchain readiness: {e}{Colors.ENDC}")
            logger.error("Blockchain readiness check error details: %s", traceback.format_exc())
            blockchain_is_ready = False
            exit_code = 1
        
        # Log startup progress
        if blockchain_is_ready:
            logger.info(f"{Colors.GREEN}Blockchain Core started successfully in {time.time() - startup_begin_time:.2f}s{Colors.ENDC}")
        else:
            logger.warning(f"{Colors.YELLOW}Blockchain Core startup timed out after {time.time() - startup_begin_time:.2f}s{Colors.ENDC}")
            # Try again with a longer timeout
            try:
                logger.info("Retrying blockchain readiness check with extended timeout...")
                # Extra time for Windows systems which might be slower
                time.sleep(3)
                blockchain_is_ready = check_blockchain_ready()
                logger.info(f"Second blockchain ready check result: {blockchain_is_ready}")
            except Exception as e:
                logger.error(f"{Colors.RED}Error in second blockchain readiness check: {e}{Colors.ENDC}")
                blockchain_is_ready = False
        
        # Decide whether to continue based on blockchain status
        continue_without_blockchain = False  # Set to True to allow startup without blockchain
        
        if blockchain_is_ready or continue_without_blockchain:
            if not blockchain_is_ready:
                logger.warning("Blockchain Core is not running properly, but continuing with other components")
            print("Starting CLI...")
            sys.stdout.flush()
            try:
                logger.info("Initializing CLI thread")
                cli_thread = threading.Thread(target=run_cli)
                cli_thread.daemon = True
                cli_thread.start()
                print("CLI thread started")
                sys.stdout.flush()
                logger.info("CLI thread started successfully with ID: %s", cli_thread.ident)
            except Exception as e:
                logger.error(f"{Colors.RED}Failed to start CLI thread: {e}{Colors.ENDC}")
                logger.error("CLI startup error details: %s", traceback.format_exc())
                exit_code = 1
                stop_event.set()  # Signal other components to stop
                return
            
            # Wait briefly to detect immediate CLI failures
            time.sleep(1)
            if exit_code != 0:
                logger.error(f"{Colors.RED}CLI startup detected an immediate failure{Colors.ENDC}")
                stop_event.set()
                return
            
            print("Starting DEX...")
            sys.stdout.flush()
            try:
                logger.info("Initializing DEX thread")
                dex_thread = threading.Thread(target=run_dex)
                dex_thread.daemon = True
                dex_thread.start()
                print("DEX thread started")
                sys.stdout.flush()
                logger.info("DEX thread started successfully with ID: %s", dex_thread.ident)
            except Exception as e:
                logger.error(f"{Colors.RED}Failed to start DEX thread: {e}{Colors.ENDC}")
                logger.error("DEX startup error details: %s", traceback.format_exc())
                exit_code = 1
                stop_event.set()  # Signal other components to stop
                return
            
            # Wait briefly to detect immediate DEX failures
            time.sleep(1)
            if exit_code != 0:
                logger.error(f"{Colors.RED}DEX startup detected an immediate failure{Colors.ENDC}")
                stop_event.set()
                return
            
            # Start monitoring thread
            # Start monitoring thread
            # Wait a moment for components to stabilize
            logger.info("Waiting for components to stabilize...")
            logger.info("Current component status - Blockchain: %s, CLI: %s, DEX: %s", 
                     "Running" if blockchain_ready.is_set() else "Not Running",
                     "Running" if cli_running else "Not Running",
                     "Running" if dex_running else "Not Running")
            time.sleep(5)  # Give more time for components to stabilize
            # Verify component status before declaring startup complete
            components_ok = True
            logger.info(f"{Colors.BLUE}Verifying component status...{Colors.ENDC}")
            
            # Check blockchain if required
            if not continue_without_blockchain and not blockchain_ready.is_set():
                logger.error(f"{Colors.RED}Blockchain Core failed to start properly{Colors.ENDC}")
                if blockchain_error:
                    logger.error(f"{Colors.RED}Blockchain error: {blockchain_error}{Colors.ENDC}")
                components_ok = False
                exit_code = 1
            
            # Check CLI
            if not cli_running:
                logger.error(f"{Colors.RED}CLI failed to start properly{Colors.ENDC}")
                components_ok = False
                exit_code = 1
            
            # Check DEX (optional)
            # Check DEX (optional)
            if not dex_running:
                logger.warning(f"{Colors.YELLOW}DEX failed to start properly (non-critical){Colors.ENDC}")
                # DEX is not critical for operation
                
            # Start monitoring thread
            try:
                logger.info("Starting component monitoring thread")
                monitor_thread = threading.Thread(target=monitor_components)
                monitor_thread.daemon = True
                monitor_thread.start()
                logger.info("Component monitoring thread started with ID: %s", monitor_thread.ident)
            except Exception as e:
                logger.error(f"{Colors.RED}Failed to start monitoring thread: {e}{Colors.ENDC}")
                logger.error("Monitoring thread error details: %s", traceback.format_exc())
                # Not critical, can continue without monitoring
                logger.warning("Continuing without component monitoring")
            logger.info("Component monitoring setup complete")
            logger.info(f"Marble DEX Web UI: http://{DEX_HOST}:{DEX_PORT}/")
            logger.info("Press Ctrl+C to stop all components")
            
            # Mark startup phase as complete to enable monitoring
            # Log detailed component status before completing startup
            status_lines = [
                f"Blockchain Core: {'[RUNNING]' if blockchain_ready.is_set() else '[NOT RUNNING]'}",
                f"CLI: {'[RUNNING]' if cli_running else '[NOT RUNNING]'}",
                f"DEX: {'[RUNNING]' if dex_running else '[NOT RUNNING]'}"
            ]
            logger.info(f"Component Status Summary:\n" + "\n".join(status_lines))
            
            # Mark startup phase as complete to enable monitoring
            component_startup_in_progress = False
            # Only set startup_complete if components started correctly
            # Only set startup_complete if components started correctly
            if components_ok:
                # Mark startup as complete - now we can properly handle signals
                startup_complete = True
                logger.info(f"{Colors.GREEN}Marble Blockchain System startup complete{Colors.ENDC}")
                # Reset exit code to ensure success if components started properly
                exit_code = 0
            else:
                logger.error(f"{Colors.RED}Marble Blockchain System startup failed{Colors.ENDC}")
                logger.error(f"{Colors.RED}Exit code: {exit_code}{Colors.ENDC}")
                stop_event.set()
                # Print to stderr for user visibility
                print(f"Error: Component startup failed with exit code {exit_code}", file=sys.stderr)
                sys.stderr.flush()
            components_status_check_time = time.time()
            
            # Monitor all components for unexpected termination
            while not stop_event.is_set():
                time.sleep(1)
                
                # Check component health periodically
                current_time = time.time()
                if current_time - components_status_check_time > 10:  # Check every 10 seconds
                    components_status_check_time = current_time
                    
                    # Check blockchain health only if it's required
                    # Only perform failure checks after startup is complete
                    if startup_complete:
                        # Check blockchain health only if it's required
                        if not blockchain_ready.is_set() and not continue_without_blockchain:
                            logger.error(f"{Colors.RED}Blockchain Core stopped running and is required{Colors.ENDC}")
                            if blockchain_error:
                                logger.error(f"{Colors.RED}Blockchain failure reason: {blockchain_error}{Colors.ENDC}")
                            component_failure_detected = True
                            break
                            
                        # Check CLI status if running
                        if not cli_running:
                            logger.error(f"{Colors.RED}CLI stopped running unexpectedly{Colors.ENDC}")
                            component_failure_detected = True
                            break
                            
                        # Check DEX status
                        if not dex_running:
                            logger.warning(f"{Colors.YELLOW}DEX is not running{Colors.ENDC}")
                            # DEX is not critical, just log a warning
                    else:
                        # If startup isn't complete yet, don't trigger failure detection
                        # Just log current status
                        status = []
                        if blockchain_ready.is_set():
                            status.append("Blockchain: Running")
                        else:
                            status.append("Blockchain: Starting...")
                            
                        if cli_running:
                            status.append("CLI: Running")
                        else:
                            status.append("CLI: Starting...")
                            
                        if dex_running:
                            status.append("DEX: Running")
                        else:
                            status.append("DEX: Starting...")
                            
                        logger.info(f"Startup progress: {' | '.join(status)}")
                
            # Handle component failure detected in the monitoring loop
            if stop_event.is_set():
                logger.info("Stop event detected, shutting down...")
            
            if component_failure_detected:
                logger.error(f"{Colors.RED}Critical component failure detected{Colors.ENDC}")
                exit_code = 1
                # stop_event already set by the monitoring loop
        else:
            logger.error(f"{Colors.RED}Failed to start blockchain and continue_without_blockchain is set to False{Colors.ENDC}")
            exit_code = 1
            
    except KeyboardInterrupt:
        # Ensure this doesn't cause an exit code 1
        logger.info("User interrupted startup with Ctrl+C")
        logger.info("Received KeyboardInterrupt, shutting down...")
        # Only set exit code to 0 if this was a clean user-initiated shutdown
        if startup_complete:
            exit_code = 0
        else:
            logger.info("Shutdown during startup phase, maintaining current exit code: " + str(exit_code))
        stop_event.set()
        
    except Exception as e:
        logger.error(f"{Colors.RED}Error in orchestrator: {e}{Colors.ENDC}", exc_info=True)
        stop_event.set()
        exit_code = 1
        
    finally:
        # Reset startup flags
        component_startup_in_progress = False
        
        # Ensure all processes are terminated
        for proc in processes:
            if proc and proc.poll() is None:
                try:
                    if sys.platform == 'win32':
                        proc.terminate()
                    else:
                        proc.send_signal(signal.SIGTERM)
                except Exception as e:
                    logger.error(f"Error during final process cleanup: {e}")
        
        # Give processes a moment to terminate
        time.sleep(0.5)
        
        # Log final status
        if exit_code == 0:
            logger.info(f"{Colors.GREEN}Marble Blockchain System Orchestrator shutdown complete (success){Colors.ENDC}")
        else:
            logger.error(f"{Colors.RED}Marble Blockchain System Orchestrator shutdown complete (with errors - exit code {exit_code}){Colors.ENDC}")
            # Print to stdout for easier diagnosis
            print(f"Marble Blockchain System exited with code {exit_code}")
            if exit_code != 0:
                print(f"Please check the logs for detailed error information.")
            sys.stdout.flush()

if __name__ == "__main__":
    try:
        main()  # Call main function which will set exit_code
        sys.exit(exit_code)  # Use the global exit_code to ensure proper exit status
    except Exception as e:
        print(f"Critical error in main execution: {e}")
        sys.exit(1)
