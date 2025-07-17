# Marble Blockchain DEX

A high-performance decentralized exchange built on the Marble Blockchain with integrated Solana support, providing secure cross-chain trading, token locking mechanisms, and real-time data visualization.

![Marble Blockchain Logo](static/logo.png)

## Features

- **Hybrid PoH+PoS Consensus Mechanism**: Fast transaction confirmation with energy-efficient validation
- **Solana Integration**: Cross-chain compatibility with the Solana blockchain
- **Solflare Wallet Support**: Seamless connection with popular Solana wallets
- **Token Locking Mechanism**: Lock tokens for staking rewards and governance participation
- **Real-time Price Charts**: Visualization using Matplotlib
- **WebSocket Order Book**: Live updates of market depth and trading activity
- **AES-256 Encryption**: Enterprise-grade security for sensitive operations
- **Cross-chain Trading**: Trade tokens between Marble and Solana ecosystems
- **CPU Performance Metrics**: Track validator performance with detailed metrics
- **Responsive UI**: Mobile-friendly trading interface

## Installation

### Prerequisites

- Python 3.8+
- Node.js 14+ (for frontend development)
- Solana CLI tools (optional, for advanced Solana interactions)

### Basic Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/marble-blockchain.git
   cd marble-blockchain
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On Unix or MacOS
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### New Dependencies

This version introduces several new dependencies:

1. **Solana Integration**:
   ```bash
   pip install solana
   ```

2. **System Monitoring**:
   ```bash
   pip install psutil
   ```

3. **Data Visualization**:
   ```bash
   pip install matplotlib pandas
   ```

4. **Web3 Libraries**:
   ```bash
   pip install web3
   ```

## Running the DEX

Start the DEX application:

```bash
python marble_dex_app.py
```

The application will be available at `http://localhost:8000` by default.

## Troubleshooting and AI Support

### Common Issues and Solutions

#### Peer Connection Warnings

When running the DEX application, you might see warnings like:

```
WARNING - Cannot request blocks: no connected peers
WARNING - Failed to synchronize blockchain with network
```

These warnings are normal during initial setup and indicate:

- The blockchain node is trying to connect to seed nodes but cannot reach them
- These warnings do not affect basic DEX UI functionality
- You can still use the DEX for trading and token operations

#### Starting the Server

There are two recommended ways to start the DEX server:

1. Using Python directly:
   ```bash
   python marble_dex_app.py
   ```

2. Using Uvicorn directly (for more control):
   ```bash
   uvicorn marble_dex_app:app --host 127.0.0.1 --port 8000
   ```

If you encounter a "port already in use" error, ensure no other instances are running:

- On Windows:
  ```powershell
  Stop-Process -Name python -Force  # To kill any existing Python processes
  # or
  netstat -ano | findstr :8000      # To find what's using port 8000
  ```

- On Unix/Linux:
  ```bash
  pkill -f "python marble_dex_app.py"
  # or
  lsof -i :8000                    # To find what's using port 8000
  ```

### Working Without Peer Connections

The DEX is designed to function in standalone mode when peer connections are unavailable:

1. Local blockchain state will be maintained
2. Trading and token operations work normally
3. Only blockchain synchronization features are limited

### AI Support

AI assistance is available to help with:

1. Diagnosing and resolving connection issues
2. Starting and configuring the DEX properly
3. Troubleshooting common errors
4. Guiding you through the setup process

To use AI support for troubleshooting, provide:

1. The exact error message you're seeing
2. The command you used to start the application
3. Information about your environment (operating system, Python version)

## Solana Integration Setup

### Configuring Solana Connection

1. Set up your Solana connection in `marble_blockchain.py`:

```python
# Default is Solana Devnet
SOLANA_DEVNET_URL = "https://api.devnet.solana.com"
# For mainnet
# SOLANA_MAINNET_URL = "https://api.mainnet-beta.solana.com"
```

2. Configure the Solana to MARBLE conversion rate:

```python
# In marble_blockchain.py
SOLANA_TO_MARBLE_RATE = 100  # 1 SOL = 100 MARBLE
```

### Connecting Solflare Wallet

1. Navigate to the DEX web interface
2. Click "Connect Wallet" in the top-right corner
3. Select Solflare from the available wallet options
4. Approve the connection request in your Solflare wallet
5. Your wallet address and balances will display in the UI

## AES-256 Security Implementation

The DEX uses AES-256 encryption for secure operations:

1. The master key is defined in `marble_blockchain.py`:
   ```python
   # In production, use environment variables for this!
   MASTER_SECRET_KEY = "your-secret-key-123"
   ```

2. Security features include:
   - Encrypted API payloads
   - Secure validator communications
   - Protected blockchain alterations
   - Transaction signature verification

3. Key rotation should be performed periodically:
   ```bash
   python tools/rotate_master_key.py --old-key OLD_KEY --new-key NEW_KEY
   ```

## Token Locking Mechanism

### Overview

The token locking mechanism allows users to lock their MARBLE tokens for a predetermined period, offering several benefits:

- **Staking Rewards**: Earn passive income from transaction fees
- **Validator Status**: Locked tokens contribute to validator selection weight
- **Governance Rights**: Participate in protocol decision-making
- **Network Security**: Increased locked supply improves overall blockchain security

### How to Lock Tokens

1. Connect your wallet to the DEX
2. Navigate to the "Lock" tab in the trading interface
3. Enter the amount of MARBLE tokens to lock (minimum 10 MARBLE)
4. Select a lock period (1 month to 1 year)
5. Approve the transaction in your wallet

### Benefits by Lock Duration

| Lock Period | APY Reward | Governance Weight | Validator Eligibility |
|-------------|------------|-------------------|------------------------|
| 1 month     | 5%         | 1x                | No                     |
| 3 months    | 8%         | 1.5x              | No                     |
| 6 months    | 12%        | 2x                | Yes (min 10,000 MARBLE)|
| 1 year      | 20%        | 3x                | Yes (min 10,000 MARBLE)|

## Creating Matplotlib Graphics

The DEX uses Matplotlib for generating custom graphics and visualizations:

```python
# Generate a swap icon
icon_path = microos.generate_icon("swap")

# Generate a lock icon
icon_path = microos.generate_icon("lock")
```

## CPU Performance Monitoring

Track validator performance with detailed metrics:

```python
# Run a VMIA task for a validator
metrics = microos.run_vmia_task("validator_address", "task_name")
print(f"CPU Effort: {metrics['cpu_metrics']['cpu_effort']}%")
```

## Project Structure

```
marble-blockchain/
├── marble_blockchain.py     # Core blockchain implementation
├── marble_dex_app.py        # FastAPI DEX application
├── microos.py               # Visualization and metrics module
├── static/                  # Static assets
│   ├── style.css            # CSS styling
│   ├── logo.png             # Marble logo
│   └── icons/               # Generated icons directory
├── templates/               # HTML templates
│   └── index.html           # Main DEX interface
└── tools/                   # Utility scripts
    ├── key_management.py    # Security key management
    └── data_migration.py    # Data migration utilities
```

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

- Website: [https://marble-blockchain.io](https://marble-blockchain.io)
- Twitter: [@MarbleBlockchain](https://twitter.com/MarbleBlockchain)
- Email: info@marble-blockchain.io

# Distributed Blockchain P2P Network with AI Integration

A comprehensive blockchain P2P network implementation with virtual machine management, AI resource optimization, and Solana wallet integration.

## Features

- **Blockchain Core**: Fully functional blockchain implementation with proof-of-work consensus
- **Virtual Machine Management**: Docker-based VM provisioning and management
- **AI Resource Optimization**: Neural circuit-based resource allocation and optimization
- **P2P Communication**: Advanced peer-to-peer networking with NAT traversal and automatic peer discovery
- **Solana Wallet Integration**: Complete wallet management with transaction support
- **Web Dashboard**: Intuitive interface for system management

## System Architecture

The system is built with a modular architecture:

```
├── micro_os/
│   ├── vm/              # VM management components
│   ├── network/         # P2P networking components
│   ├── ai/              # AI and neural circuit components
│   └── cli/             # Command-line interface
├── ai_module.py         # AI container management
├── blockchain_core.py   # Core blockchain implementation
├── network.py           # NAT traversal networking
├── wallet.py            # Solana wallet implementation
├── dashboard.py         # Web dashboard and API
└── main.py              # Main entry point
```

## Getting Started

### Prerequisites

- Python 3.8+
- Docker
- Solana CLI (optional, for wallet operations)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/blockchain-p2p-network.git
   cd blockchain-p2p-network
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

### Running the System

Start the system with default settings:

```
python main.py
```

Or customize with command-line options:

```
python main.py --host 0.0.0.0 --dashboard-port 8080 --node-id mynode1 --network devnet
```

### Available Options

- `--host`: Host IP to bind (default: 0.0.0.0)
- `--dashboard-port`: Port for web dashboard (default: 8080)
- `--api-port`: Port for API (default: 8000)
- `--p2p-port`: Port for P2P network (default: 8888)
- `--node-id`: Unique ID for this node (default: node1)
- `--network`: Solana network to connect to (choices: devnet, testnet, mainnet; default: devnet)
- `--log-level`: Logging level (choices: DEBUG, INFO, WARNING, ERROR; default: INFO)

## Using the Web Dashboard

Once started, access the web dashboard at:

```
http://localhost:8080
```

The dashboard provides:

- System status monitoring
- Blockchain management
- VM creation and management
- Wallet operations
- Network peer management

## Core Components

### BlockchainNode

Handles blockchain operations, P2P networking, and container management:

```python
# Create a blockchain node
node = BlockchainNode(node_id="node1", host="0.0.0.0", port=8888)
await node.start()
```

### VMController

Manages Docker-based virtual machines:

```python
# Create and manage VMs
vm_controller = VMController()
vm = await vm_controller.start_vm(image="ubuntu:latest", container_name="test-vm")
```

### SolanaWallet

Provides Solana blockchain integration:

```python
# Create and use Solana wallet
wallet = SolanaWallet(network="devnet")
wallet_info = await wallet.create_wallet(password="secure_password")
balance = await wallet.get_balance()
```

### P2PNetworkManager

Manages peer-to-peer communication using libp2p:
```python
# Create P2P network
network = P2PNetworkManager(
    host_ip="0.0.0.0", 
    port=8888,
    seed_nodes=[
        "seed1.marbleblockchain.io:9090",
        "seed2.marbleblockchain.io:9090",
        "seed3.marbleblockchain.io:9090"
    ],
    enable_standalone_mode=True  # Allow operation without peers
)
await network.start()
```

The network is designed to operate even without peer connections:

```python
# Check peer connection status
connected_peers = network.get_connected_peers()
print(f"Connected to {len(connected_peers)} peers")

# Add custom peer
await network.add_peer("custom.peer.example.com:9090")

# Enable or disable standalone mode
network.set_standalone_mode(enabled=True)
```
```

### NetworkManager

Provides NAT traversal with ICE/STUN:

```python
# Create network with NAT traversal
network = NetworkManager()
await network.start()
```

### LensRefractor and AIContainerManager

AI-based resource optimization:

```python
# Use AI for resource optimization
lens = LensRefractor()
ai_manager = AIContainerManager()
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- This project uses several open-source libraries and tools
- Special thanks to the Solana and libp2p communities

# Distributed Blockchain P2P Network with Micro OS

A distributed peer-to-peer network with blockchain integration, transaction capabilities, micro operating system, and GUI interface built with Python.

## Project Overview

This project implements a fully functional distributed blockchain network with P2P communication capabilities and an integrated micro operating system. It combines:

- A robust blockchain implementation with SQLite persistence
- Peer-to-peer communication using libp2p
- A modern PyQt6-based GUI for user interaction
- Transaction system for exchanging value between peers
- Chat functionality for communication
- Micro operating system with VM emulation and container management
- Neural AI integration for optimization and security

## Features

- **Blockchain Core**
  - Proof-of-work mining
  - Transaction validation
  - Chain integrity verification
  - SQLite persistence
  - Balance tracking

- **P2P Network**
  - Distributed peer discovery
  - NAT traversal
  - Message encryption
  - Reconnection logic
  - Heartbeat mechanism
  - Configurable seed nodes
  - Automatic peer discovery
  - Resilient operation without peers
  - VM-to-VM secure communication
  - AI-driven routing optimization

- **User Interface**
  - Chat messaging
  - Transaction creation
  - Account balance monitoring
  - Peer management
  - Real-time status updates
  - VM and container management dashboard

- **Micro Operating System**
  - Virtual machine emulation with circuit-based architecture
  - Container lifecycle management (start, stop, pause, resume)
  - Resource allocation and isolation
  - Performance monitoring and health checks
  - AI-driven resource optimization
  - Lens refraction logic for VM circuits

- **Neural AI Integration**
  - Transaction validation enhancement
  - Predictive congestion control
  - Anomaly detection for security
  - Adaptive resource management
  - Performance optimization

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager 
- 4GB RAM minimum (8GB recommended for running multiple VMs)
- 20GB free disk space

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/blockchain-p2p.git
   cd blockchain-p2p
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Initialize configuration:
   ```bash
   python -m src.utils.initialize_config
   ```

4. Configure micro OS settings (optional):
   ```bash
   python -m micro_os.cli.config_manager --setup
   ```

## Usage

### Running the GUI Client

The easiest way to interact with the network is through the GUI:

```bash
python -m src.gui.clientgui_merged
```

### Running the Micro OS Terminal

Access the UNIX-like terminal interface for VM and container management:

```bash
python -m micro_os.cli.terminal
```

### Running Components Separately

#### Micro OS VM Operations

```python
from micro_os.vm.vm_environment import VMEnvironment, VMState, ResourceType

# Initialize VM environment
vm = VMEnvironment(name="my_vm", resource_limits={
    ResourceType.CPU: 2,  # 2 virtual cores
    ResourceType.MEMORY: 2048,  # 2GB RAM
    ResourceType.DISK: 10240  # 10GB disk
})

# Start VM
vm.start()

# Create and execute VM circuit
circuit_id = vm.create_circuit("calculation_circuit")
vm.execute_circuit(circuit_id, {"input_data": [1, 2, 3, 4, 5]})

# Get performance metrics
metrics = vm.get_performance_metrics()
print(f"CPU usage: {metrics.cpu_usage}%")
print(f"Memory usage: {metrics.memory_usage}MB")

# Stop VM
vm.stop()
```

#### Container Management

```python
from micro_os.containers.container_manager import ContainerManager, ContainerConfig

# Initialize container manager
container_mgr = ContainerManager()

# Create container configuration
config = ContainerConfig(
    name="blockchain_node",
    image="blockchain_node_image",
    resources={"cpu": 1, "memory": 512},
    volumes=[{"host": "./data", "container": "/app/data"}]
)

# Create and start container
container_id = container_mgr.create_container(config)
container_mgr.start_container(container_id)

# Execute command in container
output = container_mgr.exec_command(container_id, "python -m src.blockchain.get_status")
print(f"Container output: {output}")

# Stop and remove container
container_mgr.stop_container(container_id)
container_mgr.remove_container(container_id)
```

#### Blockchain Operations

```python
from src.blockchain.blockchain_merged import Blockchain, Transaction

# Initialize blockchain
blockchain = Blockchain()

# Create transaction
tx = Transaction(sender="Alice", recipient="Bob", amount=5.0)
blockchain.add_transaction(tx)

# Mine pending transactions
blockchain.mine_pending_transactions(miner_address="Alice")

# Check balance
balance = blockchain.get_balance("Alice")
print(f"Alice's balance: {balance}")
```

#### Network Client

```python
from src.networking.client_merged import Client

# Initialize client
client = Client(nickname="User1")

# Connect to network
await client.connect(bootstrap_peers=["/ip4/127.0.0.1/tcp/4001/p2p/PeerID1"])

# Send message
await client.send_message("Hello, world!", message_type="CHAT")
```

## Project Structure

```
project_root/
├── config/               # Configuration files
├── docs/                 # Documentation
├── micro_os/            # Micro OS components
│   ├── ai/              # Neural AI modules
│   ├── cli/             # Terminal interface
│   ├── containers/      # Container management
│   ├── network/         # Advanced P2P and VM networking
│   └── vm/              # VM emulation and circuit management
├── src/                  # Source code
│   ├── blockchain/       # Blockchain implementation
│   ├── gui/              # GUI components
│   ├── networking/       # P2P networking
│   └── utils/            # Utility functions
└── tests/                # Test suites
    ├── blockchain/       # Blockchain tests
    ├── micro_os/         # Micro OS component tests
    └── networking/       # Network functionality tests
```

## Development

### Running Tests
```bash
python -m unittest discover tests
```

### Micro OS Component Tests

```bash
python -m unittest discover tests.micro_os
```
```

### Building Documentation

```bash
cd docs
make html
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

