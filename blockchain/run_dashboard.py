#!/usr/bin/env python3
"""
Simplified Blockchain Dashboard

This script provides a FastAPI-based dashboard for visualizing blockchain data.
It serves static files and provides API endpoints with mock data for:
- Network status
- Blockchain statistics
- VMIA visualization

Run the dashboard with:
    python run_dashboard.py
"""

import random
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Any
import datetime

# Initialize FastAPI app
app = FastAPI(
    title="Blockchain Dashboard",
    description="Dashboard for visualizing blockchain and network data",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data generators
def get_mock_network_status() -> Dict[str, Any]:
    """Generate mock network status data."""
    online_nodes = random.randint(3, 8)
    total_nodes = 10
    
    # Generate random node data
    nodes = []
    for i in range(total_nodes):
        is_online = i < online_nodes
        nodes.append({
            "id": f"node-{i+1}",
            "status": "online" if is_online else "offline",
            "last_seen": datetime.datetime.now().isoformat() if is_online else 
                (datetime.datetime.now() - datetime.timedelta(minutes=random.randint(5, 60))).isoformat(),
            "peers": random.randint(1, 6) if is_online else 0,
            "latency": random.randint(10, 200) if is_online else None
        })
    
    return {
        "online_nodes": online_nodes,
        "total_nodes": total_nodes,
        "network_health": (online_nodes / total_nodes) * 100,
        "nodes": nodes
    }

def get_mock_blockchain_stats() -> Dict[str, Any]:
    """Generate mock blockchain statistics."""
    now = datetime.datetime.now()
    
    # Generate random blocks
    blocks = []
    for i in range(5):
        timestamp = now - datetime.timedelta(minutes=i*10)
        blocks.append({
            "height": 1000 - i,
            "hash": f"0x{random.getrandbits(160):040x}",
            "timestamp": timestamp.isoformat(),
            "transactions": random.randint(5, 50),
            "size": random.randint(1000, 8000)
        })
    
    return {
        "latest_block": 1000,
        "total_transactions": random.randint(5000, 10000),
        "transactions_per_second": round(random.uniform(0.5, 5.0), 2),
        "average_block_time": random.randint(50, 150),
        "active_addresses": random.randint(100, 500),
        "latest_blocks": blocks
    }

def get_mock_vmia_visualization() -> Dict[str, Any]:
    """Generate mock VMIA neural network visualization data."""
    # Generate random layers for a neural network
    layers = []
    layer_sizes = [4, 8, 12, 8, 4]
    
    for i, size in enumerate(layer_sizes):
        nodes = []
        for j in range(size):
            nodes.append({
                "id": f"l{i}n{j}",
                "activation": round(random.uniform(0, 1), 3),
                "bias": round(random.uniform(-1, 1), 3)
            })
        
        layers.append({
            "name": f"Layer {i+1}",
            "type": "input" if i == 0 else "output" if i == len(layer_sizes)-1 else "hidden",
            "nodes": nodes
        })
    
    # Generate connections between layers
    connections = []
    for i in range(len(layer_sizes)-1):
        for j in range(layer_sizes[i]):
            for k in range(layer_sizes[i+1]):
                if random.random() > 0.3:  # 70% chance of connection
                    connections.append({
                        "source": f"l{i}n{j}",
                        "target": f"l{i+1}n{k}",
                        "weight": round(random.uniform(-1, 1), 3)
                    })
    
    return {
        "model_name": "VMIA Neural Network",
        "accuracy": round(random.uniform(0.85, 0.98), 4),
        "training_iterations": random.randint(1000, 5000),
        "layers": layers,
        "connections": connections
    }

# API endpoints
@app.get("/")
async def root():
    """Redirect to static index.html."""
    return {"message": "Welcome to the Blockchain Dashboard API"}

@app.get("/api/network/status")
async def network_status():
    """API endpoint for network status."""
    return get_mock_network_status()

@app.get("/api/blockchain/stats")
async def blockchain_stats():
    """API endpoint for blockchain statistics."""
    return get_mock_blockchain_stats()

@app.get("/api/vmia/visualization")
async def vmia_visualization():
    """API endpoint for VMIA visualization data."""
    return get_mock_vmia_visualization()

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.datetime.now().isoformat()}

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/", StaticFiles(directory="static", html=True), name="root")

# Main entry point
if __name__ == "__main__":
    print("Starting Blockchain Dashboard server...")
    uvicorn.run("run_dashboard:app", host="0.0.0.0", port=8000, reload=True)

