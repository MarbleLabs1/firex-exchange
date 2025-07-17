#!/usr/bin/env python3
"""
MicroOS Module for Marble Blockchain

This module provides functionality for Marble Blockchain's MicroOS system,
including icon generation using Matplotlib and CPU effort measurement.
"""

import os
import time
import logging
import traceback
from pathlib import Path
from typing import Dict, Any, Optional, Union

# Import matplotlib for icon generation
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.path import Path as MplPath

# Import psutil for CPU measurements
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MarbleMicroOS")

# Constants
ICON_COLOR = "#FF0000"  # Red color for icons
STATIC_DIR = "static"
SWAP_ICON_PATH = f"{STATIC_DIR}/icon_swap.png"
LOCK_ICON_PATH = f"{STATIC_DIR}/icon_lock.png"

def ensure_static_dir() -> None:
    """
    Ensure the static directory exists for saving icons.
    """
    try:
        Path(STATIC_DIR).mkdir(exist_ok=True)
        logger.info(f"Ensured static directory exists at {STATIC_DIR}")
    except Exception as e:
        logger.error(f"Failed to create static directory: {e}")
        raise

def generate_icon(task: str) -> Optional[str]:
    """
    Generate icon using Matplotlib based on the task type.
    
    Args:
        task: Type of icon to generate ('swap' or 'lock')
        
    Returns:
        Path to the generated icon file or None if generation failed
    
    Raises:
        ValueError: If task type is not supported
    """
    logger.info(f"Generating {task} icon")
    
    try:
        # Ensure static directory exists
        ensure_static_dir()
        
        # Set DPI for high quality output
        dpi = 100
        
        if task.lower() == "swap":
            # Create swap (arrow) icon
            fig, ax = plt.subplots(figsize=(2, 2), dpi=dpi)
            
            # Create the arrow
            arrow = patches.FancyArrowPatch(
                (0.2, 0.8), (0.8, 0.2),  # start and end points
                arrowstyle='->,head_width=0.15,head_length=0.15',
                linewidth=5,
                color=ICON_COLOR,
                transform=ax.transAxes
            )
            ax.add_patch(arrow)
            
            # Add opposite small arrow to indicate swap
            small_arrow = patches.FancyArrowPatch(
                (0.7, 0.9), (0.3, 0.5),  # start and end points
                arrowstyle='->,head_width=0.1,head_length=0.1',
                linewidth=3,
                color=ICON_COLOR,
                transform=ax.transAxes
            )
            ax.add_patch(small_arrow)
            
            # Configure plot
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            fig.tight_layout(pad=0)
            
            # Save the figure
            plt.savefig(SWAP_ICON_PATH, transparent=True)
            plt.close(fig)
            logger.info(f"Swap icon generated and saved to {SWAP_ICON_PATH}")
            return SWAP_ICON_PATH
            
        elif task.lower() == "lock":
            # Create lock icon
            fig, ax = plt.subplots(figsize=(2, 2), dpi=dpi)
            
            # Create the lock body
            lock_body = patches.Rectangle(
                (0.3, 0.1), 0.4, 0.4,  # (x, y), width, height
                linewidth=2,
                edgecolor=ICON_COLOR,
                facecolor=ICON_COLOR,
                alpha=0.7,
                transform=ax.transAxes
            )
            
            # Create the lock shackle (the top part of the padlock)
            vertices = [
                (0.35, 0.5),  # Starting point at the top of the lock body
                (0.35, 0.7),  # Up
                (0.35, 0.8),  # Up more
                (0.4, 0.9),   # Right and up (curve start)
                (0.6, 0.9),   # Right (curve top)
                (0.65, 0.8),  # Right and down (curve end)
                (0.65, 0.7),  # Down
                (0.65, 0.5),  # Down to the lock body
            ]
            codes = [MplPath.MOVETO] + [MplPath.LINETO] * 7
            lock_shackle = patches.PathPatch(
                MplPath(vertices, codes),
                linewidth=3,
                edgecolor=ICON_COLOR,
                facecolor='none',
                transform=ax.transAxes
            )
            
            # Add elements to plot
            ax.add_patch(lock_body)
            ax.add_patch(lock_shackle)
            
            # Add a keyhole for detail
            keyhole_circle = patches.Circle(
                (0.5, 0.3), 0.05,
                linewidth=1,
                edgecolor='white',
                facecolor='white',
                transform=ax.transAxes
            )
            keyhole_rect = patches.Rectangle(
                (0.48, 0.15), 0.04, 0.15,
                linewidth=1,
                edgecolor='white',
                facecolor='white',
                transform=ax.transAxes
            )
            ax.add_patch(keyhole_circle)
            ax.add_patch(keyhole_rect)
            
            # Configure plot
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            fig.tight_layout(pad=0)
            
            # Save the figure
            plt.savefig(LOCK_ICON_PATH, transparent=True)
            plt.close(fig)
            logger.info(f"Lock icon generated and saved to {LOCK_ICON_PATH}")
            return LOCK_ICON_PATH
            
        else:
            raise ValueError(f"Unsupported task type: {task}. Use 'swap' or 'lock'.")
    
    except Exception as e:
        logger.error(f"Error generating {task} icon: {e}")
        logger.error(traceback.format_exc())
        return None

def run_vmia_task(validator: str, task: str) -> Dict[str, Any]:
    """
    Run a Virtual Machine Intelligence Augmentation (VMIA) task and measure CPU effort.
    
    Args:
        validator: The validator address executing the task
        task: The type of task to execute ('swap' or 'lock')
        
    Returns:
        Dictionary containing CPU metrics and task information
    """
    logger.info(f"Running VMIA task '{task}' for validator {validator}")
    
    result = {
        "validator": validator,
        "task": task,
        "status": "failed",
        "cpu_metrics": {},
        "timestamp": time.time(),
        "icon_path": None
    }
    
    try:
        # Get initial CPU measurements
        cpu_percent_start = psutil.cpu_percent(interval=0.1)
        start_time = time.time()
        process = psutil.Process(os.getpid())
        cpu_times_start = process.cpu_times()
        
        # Generate the appropriate icon based on task
        icon_path = generate_icon(task)
        if not icon_path:
            raise RuntimeError(f"Failed to generate icon for task: {task}")
        
        # Get final CPU measurements
        cpu_percent_end = psutil.cpu_percent(interval=0.1)
        end_time = time.time()
        cpu_times_end = process.cpu_times()
        
        # Calculate CPU usage metrics
        execution_time = end_time - start_time
        user_time_used = cpu_times_end.user - cpu_times_start.user
        system_time_used = cpu_times_end.system - cpu_times_start.system
        total_cpu_time = user_time_used + system_time_used
        cpu_effort = total_cpu_time / execution_time * 100
        
        # Update result with metrics
        result.update({
            "status": "success",
            "icon_path": icon_path,
            "cpu_metrics": {
                "execution_time_seconds": execution_time,
                "cpu_percent_start": cpu_percent_start,
                "cpu_percent_end": cpu_percent_end,
                "cpu_percent_change": cpu_percent_end - cpu_percent_start,
                "user_time_used": user_time_used,
                "system_time_used": system_time_used,
                "total_cpu_time": total_cpu_time,
                "cpu_effort": cpu_effort
            }
        })
        
        logger.info(f"VMIA task completed. CPU effort: {cpu_effort:.2f}%")
        
    except Exception as e:
        logger.error(f"Error running VMIA task: {e}")
        logger.error(traceback.format_exc())
        result["error"] = str(e)
    
    return result

def get_system_resources() -> Dict[str, Any]:
    """
    Get current system resource usage information.
    
    Returns:
        Dictionary containing system resource metrics
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_percent": cpu_percent,
            "memory": {
                "total_mb": memory.total / (1024 * 1024),
                "available_mb": memory.available / (1024 * 1024),
                "used_mb": memory.used / (1024 * 1024),
                "percent": memory.percent
            },
            "disk": {
                "total_gb": disk.total / (1024 * 1024 * 1024),
                "used_gb": disk.used / (1024 * 1024 * 1024),
                "free_gb": disk.free / (1024 * 1024 * 1024),
                "percent": disk.percent
            },
            "network": {
                "connections": len(psutil.net_connections())
            },
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Error getting system resources: {e}")
        return {"error": str(e)}

# Testing function - uncomment to test functionality
'''
if __name__ == "__main__":
    # Test icon generation
    swap_path = generate_icon("swap")
    lock_path = generate_icon("lock")
    
    # Test VMIA task
    metrics = run_vmia_task("test_validator_address", "swap")
    print(f"VMIA task metrics: {metrics}")
    
    # Test system resources
    resources = get_system_resources()
    print(f"System resources: {resources}")
'''

def get_vmia_status() -> Dict[str, Any]:
    """
    Get the current VMIA status including CPU/memory usage and icon paths.
    
    Returns:
        Dictionary containing:
        - cpu_percent: Current CPU usage percentage
        - memory_percent: Current memory usage percentage
        - icons: List of icon paths generated by the VMIA system
    """
    try:
        # Get CPU and memory metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        
        # Create response with metrics and icon paths
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "icons": [SWAP_ICON_PATH, LOCK_ICON_PATH],
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Error getting VMIA status: {e}")
        return {
            "error": str(e),
            "cpu_percent": 0,
            "memory_percent": 0,
            "icons": []
        }

