import asyncio
import logging
import socket
import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Union, Any
import json
from pathlib import Path
import os
import time
import sqlite3
from blockchain_core import BlockchainNode
from micro_os.vm.controller_native import VMController
from micro_os.network.p2p_vm import P2PNetworkManager
from micro_os.ai.circuits import LensRefractor
from ai_module import AIContainerManager, ContainerSpec
from wallet import SolanaWallet
from network import NetworkManager

class DashboardConfig(BaseModel):
    node_id: str = "node1"
    host: str = "0.0.0.0"
    api_port: int = 8000
    p2p_port: int = 8888
    dashboard_port: int = 8080
    solana_network: str = "devnet"
    enable_vmia: bool = False
    neural_mining: bool = False

class SystemStatus(BaseModel):
    status: str
    version: str
    uptime: float
    blockchain: Dict
    network: Dict
    resources: Dict

class VMIAConfig(BaseModel):
    temperature: float = 1.0
    max_batch_size: int = 32
    lens_depth: float = 0.7
    refraction_factor: float = 1.0
    algorithm: str = "pow"  # pow or pos

class MiningStrategy(BaseModel):
    strategy: str = "normal"  # normal, aggressive, conservative
    cpu_limit: float = 0.7
    adaptive: bool = True

class DashboardManager:
    """
    Manages the web dashboard and API endpoints for the system.
    Handles automatic port selection and component initialization.
    """
    def __init__(self, config: Optional[DashboardConfig] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or DashboardConfig()
        self.components = {}
        self._db_path = Path("dashboard_state.db")
        self._init_db()
        self._load_state()
        self.start_time = time.time()
        self.app = FastAPI(
            title="Blockchain P2P Dashboard",
            description="Web dashboard for managing blockchain P2P network",
            version="1.0.0"
        )
        self._setup_routes()
        self._setup_websocket()
    
    def _setup_routes(self):
        """Set up FastAPI routes for the dashboard API."""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def root():
            """Serve the dashboard HTML page."""
            try:
                html_path = Path("static/index.html")
                if html_path.exists():
                    return HTMLResponse(content=html_path.read_text(), status_code=200)
                else:
                    # If file doesn't exist, return placeholder
                    return HTMLResponse(content=self._get_placeholder_html(), status_code=200)
            except Exception as e:
                self.logger.error(f"Error serving dashboard: {str(e)}")
                return HTMLResponse(content="<html><body><h1>Error loading dashboard</h1></body></html>", status_code=500)
        
        @self.app.get("/api/status")
        async def get_status():
            """Get current system status."""
            try:
                blockchain = self.components.get("blockchain")
                blockchain_status = {}
                if blockchain:
                    blockchain_status = await blockchain.get_chain_status()
                
                return SystemStatus(
                    status="running",
                    version="1.0.0",
                    uptime=time.time() - self.start_time,
                    blockchain=blockchain_status,
                    network={
                        "peers": len(getattr(self.components.get("network_manager", {}), "peers", {}))
                    },
                    resources={
                        "cpu": 0.0,  # Placeholder for actual resource monitoring
                        "memory": 0.0,
                        "disk": 0.0
                    }
                )
            except Exception as e:
                self.logger.error(f"Error getting status: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/start")
        async def start_system():
            """Start all system components."""
            try:
                if not self.components:
                    await self.init_components()
                
                return {"status": "started", "components": list(self.components.keys())}
            except Exception as e:
                self.logger.error(f"Error starting system: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/stop")
        async def stop_system():
            """Stop all system components."""
            try:
                await self.cleanup_components()
                return {"status": "stopped"}
            except Exception as e:
                self.logger.error(f"Error stopping system: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # VM management endpoints
        @self.app.get("/api/vms")
        async def list_vms():
            """List all VMs."""
            try:
                vm_controller = self.components.get("vm_controller")
                if not vm_controller:
                    raise HTTPException(status_code=400, detail="VM controller not initialized")
                
                vms = await vm_controller.list_vms()
                return {"vms": vms}
            except Exception as e:
                self.logger.error(f"Error listing VMs: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/vms/start")
        async def start_vm(vm_config: Dict):
            """Start a new VM."""
            try:
                vm_controller = self.components.get("vm_controller")
                if not vm_controller:
                    raise HTTPException(status_code=400, detail="VM controller not initialized")
                
                result = await vm_controller.start_vm(
                    image=vm_config.get("image"),
                    container_name=vm_config.get("name"),
                    resources=vm_config.get("resources")
                )
                return result
            except Exception as e:
                self.logger.error(f"Error starting VM: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Blockchain endpoints
        @self.app.get("/api/blockchain/status")
        async def get_blockchain_status():
            """Get blockchain status."""
            try:
                blockchain = self.components.get("blockchain")
                if not blockchain:
                    raise HTTPException(status_code=400, detail="Blockchain not initialized")
                
                status = await blockchain.get_chain_status()
                return status
            except Exception as e:
                self.logger.error(f"Error getting blockchain status: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/blockchain/transaction")
        async def submit_transaction(transaction: Dict):
            """Submit a new transaction."""
            try:
                blockchain = self.components.get("blockchain")
                if not blockchain:
                    raise HTTPException(status_code=400, detail="Blockchain not initialized")
                
                result = await blockchain.submit_transaction(transaction)
                return result
            except Exception as e:
                self.logger.error(f"Error submitting transaction: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Wallet endpoints
        @self.app.post("/api/wallet/create")
        async def create_wallet(wallet_config: Dict):
            """Create a new wallet."""
            try:
                wallet = self.components.get("wallet") or SolanaWallet(network=wallet_config.get("network", "devnet"))
                self.components["wallet"] = wallet
                
                result = await wallet.create_wallet(wallet_config.get("password", ""))
                return result
            except Exception as e:
                self.logger.error(f"Error creating wallet: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/wallet/balance")
        async def get_wallet_balance():
            """Get wallet balance."""
            try:
                wallet = self.components.get("wallet")
                if not wallet:
                    raise HTTPException(status_code=400, detail="Wallet not initialized")
                
                balance = await wallet.get_balance()
                return {"balance": balance}
            except Exception as e:
                self.logger.error(f"Error getting wallet balance: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Mount static files for dashboard
        try:
            static_dir = Path("static")
            if not static_dir.exists():
                static_dir.mkdir(parents=True)
            self.app.mount("/static", StaticFiles(directory="static"), name="static")
        except Exception as e:
            self.logger.error(f"Error mounting static files: {str(e)}")

        # Add AI/VMIA management endpoints
        @self.app.get("/api/vmia/status")
        async def get_vmia_status():
            """Get current VMIA neural network status."""
            try:
                lens = self.components.get("lens_refractor")
                if not lens:
                    raise HTTPException(status_code=400, detail="Lens refractor not initialized")
                
                return {
                    "temperature": lens.temperature,
                    "lens_depth": lens.lens_depth,
                    "refraction_factor": lens.refraction_factor,
                    "active_neurons": lens.get_active_neurons_count()
                }
            except Exception as e:
                self.logger.error(f"Error getting VMIA status: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/vmia/configure")
        async def configure_vmia(config: VMIAConfig):
            """Configure VMIA neural network parameters."""
            try:
                lens = self.components.get("lens_refractor")
                if not lens:
                    raise HTTPException(status_code=400, detail="Lens refractor not initialized")
                
                lens.temperature = config.temperature
                lens.lens_depth = config.lens_depth
                lens.refraction_factor = config.refraction_factor
                lens.set_algorithm(config.algorithm)
                return {"status": "configured"}
            except Exception as e:
                self.logger.error(f"Error configuring VMIA: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/vmia/visualization")
        async def get_vmia_visualization():
            """Get visualization data for the VMIA neural network."""
            try:
                lens = self.components.get("lens_refractor")
                if not lens:
                    raise HTTPException(status_code=400, detail="Lens refractor not initialized")
                
                return lens.get_visualization_data()
            except Exception as e:
                self.logger.error(f"Error getting VMIA visualization: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/mining/configure")
        async def configure_mining(strategy: MiningStrategy):
            """Configure mining strategy."""
            try:
                blockchain = self.components.get("blockchain")
                if not blockchain:
                    raise HTTPException(status_code=400, detail="Blockchain not initialized")
                
                await blockchain.set_mining_strategy(
                    strategy=strategy.strategy,
                    cpu_limit=strategy.cpu_limit,
                    adaptive=strategy.adaptive
                )
                return {"status": "configured"}
            except Exception as e:
                self.logger.error(f"Error configuring mining: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/transactions/analysis")
        async def analyze_transactions():
            """Analyze transactions patterns."""
            try:
                blockchain = self.components.get("blockchain")
                if not blockchain:
                    raise HTTPException(status_code=400, detail="Blockchain not initialized")
                
                return await blockchain.analyze_transaction_patterns()
            except Exception as e:
                self.logger.error(f"Error analyzing transactions: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
    
    def _setup_websocket(self):
        """Set up WebSocket for real-time updates."""
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            try:
                while True:
                    # Periodically send system status updates
                    blockchain = self.components.get("blockchain")
                    status = {
                        "blockchain": await blockchain.get_chain_status() if blockchain else {},
                        "resources": {
                            "cpu": 0.0,  # Placeholder for actual resource monitoring
                            "memory": 0.0,
                            "disk": 0.0
                        }
                    }
                    await websocket.send_json(status)
                    await asyncio.sleep(2)
            except WebSocketDisconnect:
                self.logger.info("WebSocket client disconnected")
            except Exception as e:
                self.logger.error(f"WebSocket error: {str(e)}")
    
    def _get_placeholder_html(self) -> str:
        html_path = Path("static/index.html")
        if html_path.exists():
            return html_path.read_text()
            
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Blockchain P2P Network Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/vue@3.2.31/dist/vue.global.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.3.2/dist/echarts.min.js"></script>
    <script src="https://unpkg.com/axios/dist/axios.min.js"></script>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        .chart-container {
            height: 400px;
            width: 100%;
        }
        .card {
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 20px;
            margin-bottom: 20px;
            background: white;
        }
        .slider-container {
            padding: 15px 0;
        }
        .control-panel {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }
        .panel-section {
            margin-bottom: 30px;
        }
    </style>
</head>
<body>
    <div id="app">
        <header class="bg-dark text-white p-3 mb-4">
            <h1>Blockchain P2P Network Dashboard</h1>
            <div>Node: {{ nodeId }} | Status: {{ systemStatus.status }}</div>
        </header>
        
        <div class="container">
            <!-- Main System Controls -->
            <div class="card">
                <h2>System Status</h2>
                <div class="control-panel">
                    <button @click="startSystem" class="btn btn-primary">Start System</button>
                    <button @click="stopSystem" class="btn btn-danger">Stop System</button>
                </div>
                <div class="mt-3">
                    <p>Version: {{ systemStatus.version }} | Uptime: {{ formatUptime(systemStatus.uptime) }}</p>
                    <p>Blockchain Height: {{ blockchainStatus.height }} | Peers: {{ systemStatus.network.peers }}</p>
                </div>
            </div>
            
            <!-- Neural Network Controls -->
            <div class="card panel-section">
                <h2>VMIA Neural Network</h2>
                <div class="grid">
                    <div>
                        <h4>Parameters</h4>
                        <div class="slider-container">
                            <label>Temperature: {{ vmiaConfig.temperature.toFixed(2) }}</label>
                            <input type="range" v-model="vmiaConfig.temperature" min="0" max="2" step="0.1" class="form-range">
                        </div>
                        <div class="slider-container">
                            <label>Lens Depth: {{ vmiaConfig.lens_depth.toFixed(2) }}</label>
                            <input type="range" v-model="vmiaConfig.lens_depth" min="0" max="1" step="0.05" class="form-range">
                        </div>
                        <div class="slider-container">
                            <label>Refraction: {{ vmiaConfig.refraction_factor.toFixed(2) }}</label>
                            <input type="range" v-model="vmiaConfig.refraction_factor" min="0.5" max="2" step="0.1" class="form-range">
                        </div>
                        <div class=\"mt-3\"></div>
                    """
                    
    def get_dashboard_html():
        """Return placeholder HTML for dashboard."""
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Blockchain P2P Network Dashboard</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: #f5f5f5;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }
                header {
                    background-color: #2c3e50;
                    color: white;
                    padding: 20px;
                    text-align: center;
                }
                .card {
                    background-color: white;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    padding: 20px;
                    margin-bottom: 20px;
                }
                .button {
                    background-color: #3498db;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    cursor: pointer;
                }
                .button:hover {
                    background-color: #2980b9;
                }
                .grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 20px;
                }
            </style>
        </head>
        <body>
            <header>
                <h1>Blockchain P2P Network Dashboard</h1>
            </header>
            <div class="container">
                <div class="card">
                    <h2>System Status</h2>
                    <div id="status">Loading...</div>
                    <button class="button" id="startBtn">Start System</button>
                    <button class="button" id="stopBtn">Stop System</button>
                </div>
                
                <div class="grid">
                    <div class="card">
                        <h2>Blockchain</h2>
                        <div id="blockchain">Loading...</div>
                    </div>
                    
                    <div class="card">
                        <h2>Network</h2>
                        <div id="network">Loading...</div>
                    </div>
                    
                    <div class="card">
                        <h2>Resources</h2>
                        <div id="resources">Loading...</div>
                    </div>
                </div>
                
                <div class="card">
                    <h2>VM Management</h2>
                    <div id="vms">Loading...</div>
                    <h3>Start New VM</h3>
                    <form id="vmForm">
                        <input type="text" placeholder="Image" id="vmImage" required>
                        <input type="text" placeholder="Name" id="vmName">
                        <button type="submit" class="button">Start VM</button>
                    </form>
                </div>
                
                <div class="card">
                    <h2>Wallet</h2>
                    <div id="wallet">Loading...</div>
                    <button class="button" id="createWalletBtn">Create Wallet</button>
                    <button class="button" id="balanceBtn">Check Balance</button>
                </div>
            </div>
            <script>
                // Simple dashboard JavaScript
                document.addEventListener('DOMContentLoaded', function() {
                    // Connect to WebSocket for real-time updates
                    const ws = new WebSocket(`ws://${window.location.host}/ws`);
                    
                    ws.onmessage = function(event) {
                        const data = JSON.parse(event.data);
                        
                        // Update blockchain info
                        if (data.blockchain) {
                            document.getElementById('blockchain').innerHTML = `
                                <p>Height: ${data.blockchain.height || 0}</p>
                                <p>Pending Transactions: ${data.blockchain.pending_transactions || 0}</p>
                                <p>Peers: ${data.blockchain.peers || 0}</p>
                            `;
                        }
                        
                        // Update resource info
                        if (data.resources) {
                            document.getElementById('resources').innerHTML = `
                                <p>CPU: ${data.resources.cpu || 0}%</p>
                                <p>Memory: ${data.resources.memory || 0}MB</p>
                                <p>Disk: ${data.resources.disk || 0}GB</p>
                            `;
                        }
                    };
                    
                    // Fetch initial system status
                    fetch('/api/status')
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('status').innerHTML = `
                                <p>Status: ${data.status}</p>
                                <p>Version: ${data.version}</p>
                                <p>Uptime: ${Math.round(data.uptime / 60)} minutes</p>
                            `;
                            
                            document.getElementById('network').innerHTML = `
                                <p>Connected Peers: ${data.network.peers || 0}</p>
                            `;
                        })
                        .catch(error => {
                            console.error('Error fetching status:', error);
                            document.getElementById('status').textContent = 'Error loading status';
                        });
                    
                    // Fetch VMs
                    fetch('/api/vms')
                        .then(response => response.json())
                        .then(data => {
                            const vms = data.vms || [];
                            if (vms.length === 0) {
                                document.getElementById('vms').textContent = 'No VMs running';
                            } else {
                                document.getElementById('vms').innerHTML = vms.map(vm => `
                                    <div>
                                        <p>ID: ${vm.container_id}</p>
                                        <p>Name: ${vm.name}</p>
                                        <p>Status: ${vm.status}</p>
                                    </div>
                                `).join('');
                            }
                        })
                        .catch(error => {
                            console.error('Error fetching VMs:', error);
                            document.getElementById('vms').textContent = 'Error loading VMs';
                        });
                    
                    // Start System Button
                    document.getElementById('startBtn').addEventListener('click', function() {
                        fetch('/api/start', {
                            method: 'POST',
                        })
                        .then(response => response.json())
                        .then(data => {
                            alert('System started');
                            location.reload();
                        })
                        .catch(error => {
                            console.error('Error starting system:', error);
                            alert('Error starting system');
                        });
                    });
                    
                    // Stop System Button
                    document.getElementById('stopBtn').addEventListener('click', function() {
                        fetch('/api/stop', {
                            method: 'POST',
                        })
                        .then(response => response.json())
                        .then(data => {
                            alert('System stopped');
                            location.reload();
                        })
                        .catch(error => {
                            console.error('Error stopping system:', error);
                            alert('Error stopping system');
                        });
                    });
                    
                    // VM Form
                    document.getElementById('vmForm').addEventListener('submit', function(e) {
                        e.preventDefault();
                        const image = document.getElementById('vmImage').value;
                        const name = document.getElementById('vmName').value;
                        
                        fetch('/api/vms/start', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                image: image,
                                name: name,
                                resources: {
                                    cpu_count: 1,
                                    mem_limit: '512m',
                                    network_mode: 'bridge'
                                }
                            }),
                        })
                        .then(response => response.json())
                        .then(data => {
                            alert('VM started');
                            location.reload();
                        })
                        .catch(error => {
                            console.error('Error starting VM:', error);
                            alert('Error starting VM');
                        });
                    });
                    
                    // Create Wallet Button
                    document.getElementById('createWalletBtn').addEventListener('click', function() {
                        const password = prompt('Enter wallet password:');
                        if (!password) return;
                        
                        fetch('/api/wallet/create', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                password: password,
                                network: 'devnet'
                            }),
                        })
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('wallet').innerHTML = `
                                <p>Address: ${data.address}</p>
                                <p>Network: ${data.network}</p>
                            `;
                            alert('Wallet created');
                        })
                        .catch(error => {
                            console.error('Error creating wallet:', error);
                            alert('Error creating wallet');
                        });
                    });
                    
                    // Check Balance Button
                    document.getElementById('balanceBtn').addEventListener('click', function() {
                        fetch('/api/wallet/balance')
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('wallet').innerHTML += `
                                <p>Balance: ${data.balance} SOL</p>
                            `;
                        })
                        .catch(error => {
                            console.error('Error checking balance:', error);
                            alert('Error checking balance');
                        });
                    });
                });
            </script>
        </body>
        </html>
        """

    async def find_free_port(self, start_port: int, max_attempts: int = 10) -> int:
        """Find a free port starting from start_port."""
        for port in range(start_port, start_port + max_attempts):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('0.0.0.0', port))
                    return port
                except socket.error:
                    continue
        raise RuntimeError(f"Could not find a free port in range {start_port}-{start_port + max_attempts}")

    async def init_components(self):
        """Initialize all system components with auto port selection."""
        try:
            # Find free ports for services
            api_port = await self.find_free_port(self.config.api_port)
            p2p_port = await self.find_free_port(self.config.p2p_port)
            dashboard_port = await self.find_free_port(self.config.dashboard_port)
            
            self.logger.info(f"Using ports: API={api_port}, P2P={p2p_port}, Dashboard={dashboard_port}")
            
            # Initialize components
            self.components["vm_controller"] = VMController()
            
            # Initialize P2P network
            network_manager = P2PNetworkManager(host_ip=self.config.host, port=p2p_port)
            await network_manager.start()
            self.components["network_manager"] = network_manager
            
            # Initialize blockchain
            blockchain = BlockchainNode(
                node_id=self.config.node_id,
                host=self.config.host,
                port=p2p_port
            )
            await blockchain.start()
            self.components["blockchain"] = blockchain
            
            # Initialize wallet
            wallet = SolanaWallet(network=self.config.solana_network)
            self.components["wallet"] = wallet
            
            # Initialize AI components
            self.components["lens_refractor"] = LensRefractor()
            self.components["ai_manager"] = AIContainerManager()
            
            return {
                "status": "initialized",
                "ports": {
                    "api": api_port,
                    "p2p": p2p_port,
                    "dashboard": dashboard_port
                }
            }
        
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {str(e)}")
            raise RuntimeError(f"Component initialization failed: {str(e)}")

    async def cleanup_components(self):
        """Clean up and close all components."""
        try:
            self._save_state()
            if "wallet" in self.components:
                await self.components["wallet"].close()
            
            if "network_manager" in self.components:
                # Close connections if method exists
                if hasattr(self.components["network_manager"], "cleanup"):
                    await self.components["network_manager"].cleanup()
            
            self.components.clear()
            return {"status": "cleaned_up"}
        
        except Exception as e:
            self.logger.error(f"Failed to clean up components: {str(e)}")
            raise RuntimeError(f"Component cleanup failed: {str(e)}")

    async def start_dashboard(self):
        """Start the dashboard server."""
        try:
            # Find a free port for the dashboard
            dashboard_port = await self.find_free_port(self.config.dashboard_port)
            self.logger.info(f"Starting dashboard on port {dashboard_port}")
            
            # Initialize components if not already initialized
            if not self.components:
                await self.init_components()
            
            config = uvicorn.Config(
                host=self.config.host,
                port=dashboard_port,
                log_level="info"
            )
            server = uvicorn.Server(config)
            await server.serve()
            
        except Exception as e:
            self.logger.error(f"Failed to start dashboard: {str(e)}")
            raise RuntimeError(f"Dashboard start failed: {str(e)}")


    def _init_db(self):
        """Initialize SQLite database with required tables."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS component_status (
                    component TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS port_mappings (
                    service TEXT PRIMARY KEY,
                    port INTEGER NOT NULL
                )
            """)
            conn.commit()

    def _save_state(self):
        """Save current state to SQLite database."""
        try:
            with sqlite3.connect(self._db_path) as conn:
                # Save component statuses
                for component, instance in self.components.items():
                    status = {
                        'status': 'active',
                        'type': type(instance).__name__
                    }
                    conn.execute(
                        "INSERT OR REPLACE INTO component_status VALUES (?, ?, ?)",
                        (component, 'active', json.dumps(status))
                    )

                # Save port mappings
                if 'network_manager' in self.components:
                    nm = self.components['network_manager']
                    conn.execute(
                        "INSERT OR REPLACE INTO port_mappings VALUES (?, ?)",
                        ('p2p', nm.port)
                    )
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error saving state: {str(e)}")

    def _load_state(self):
        """Load stored state from SQLite database."""
        try:
            with sqlite3.connect(self._db_path) as conn:
                # Load port mappings
                cur = conn.execute("SELECT service, port FROM port_mappings")
                for service, port in cur.fetchall():
                    if service == 'p2p':
                        self.config.p2p_port = port
        except Exception as e:
            self.logger.error(f"Error loading state: {str(e)}")
            
    def run(self):
        """Run the dashboard synchronously."""
        try:
            # Find a free port
            dashboard_port = asyncio.run(self.find_free_port(self.config.dashboard_port))
            
            # Start Uvicorn server
            uvicorn.run(
                self.app,
                host=self.config.host,
                port=dashboard_port,
                log_level="info",
                log_config="logging.conf"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to run dashboard: {str(e)}")
            raise RuntimeError(f"Dashboard run failed: {str(e)}")


# Main entry point for the dashboard
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    
    # Create and run dashboard
    dashboard = DashboardManager()
    dashboard.run()
