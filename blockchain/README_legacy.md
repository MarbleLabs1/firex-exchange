# Marble DEX Implementation

A Raydium V3-like decentralized exchange implementation with blockchain validation capabilities.

## Features

- **Modern UI**: Streamlit-based interface with Raydium-like styling
- **Token Swapping**: Easy-to-use token swap interface
- **Order Book**: Real-time order book visualization
- **Block Validation**: Advanced blockchain validation tools
- **Wallet Integration**: Mock wallet connection for testing

## Architecture

The application consists of two main components:

1. **Backend (FastAPI)**
   - `/dex_config`: Returns DEX configuration (name, color, logo, trading pairs)
   - `/trade`: Provides order book data (bids/asks)
   - Advanced blockchain validation endpoints
   - Running on port 8000

2. **Frontend (Streamlit)**
   - Modern, responsive UI
   - Three main tabs: Swap, Validate, Order Book
   - Real-time data updates
   - Running on port 8501

## Setup Instructions

1. **Install Dependencies**
   ```bash
   pip install fastapi uvicorn streamlit pandas requests
   ```

2. **Start the Backend**
   ```bash
   uvicorn marble_dex_app:app --host 0.0.0.0 --port 8000
   ```

3. **Start the Frontend**
   ```bash
   streamlit run ui.py
   ```

4. **Access the Application**
   - Frontend UI: http://localhost:8501
   - Backend API: http://localhost:8000/docs

## API Endpoints

### DEX Configuration (`/dex_config`)

Returns standardized DEX configuration:
```json
{
    "dex": "Marble DEX",
    "color": "#FF0000",
    "logo": "/static/logo.png",
    "pairs": ["MARBLE/USDT", "ETH/USDT"]
}
```

### Trade Data (`/trade`)

Returns order book data:
```json
{
    "bids": [
        {"price": 1.0, "amount": 10}
    ],
    "asks": [
        {"price": 1.1, "amount": 5}
    ]
}
```

## Styling

The application uses a custom CSS theme (in `static/style.css`) that provides:

- Consistent dark theme
- Raydium-like UI components
- Responsive design
- Custom button and input styling
- Professional table formatting

## Development

To modify the application:

1. Backend changes: Edit `marble_dex_app.py`
2. Frontend changes: Edit `ui.py`
3. Styling changes: Edit `static/style.css`

## Testing

1. Test the backend API:
   ```bash
   curl http://localhost:8000/dex_config
   curl http://localhost:8000/trade
   ```

2. Run the frontend and test all features:
   - Token swapping
   - Block validation
   - Order book updates

# Marble Blockchain

## Overview

Marble Blockchain is a CLI-driven, high-performance blockchain platform inspired by major chains like Solana, Ethereum, and BSC. Built with a focus on speed, usability, and developer experience, Marble aims to provide a robust infrastructure for decentralized applications and financial services.

The project takes a CLI-first approach, offering powerful command-line tools that make blockchain interaction intuitive and efficient. Whether you're a developer, validator, or user, Marble's command-line interface provides all the functionality you need without unnecessary complexity.

## Setup Instructions

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/your-username/marble-blockchain.git
   cd marble-blockchain
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Start the Marble CLI:
   ```
   python marble_cli.py
   ```

## CLI Commands and Usage

Marble Blockchain comes with a comprehensive set of CLI commands that allow you to interact with the blockchain, manage transactions, and perform various operations.

### Core Commands

- **start_node** - Initialize a blockchain node with mock P2P networking
  ```
  start_node
  ```

- **send** - Create and send a transaction
  ```
  send <sender_address> <recipient_address> <amount> <token>
  ```
  Example: `send addr1 addr2 10 MARBLE`

- **balance** - Check the balance of an address
  ```
  balance <address>
  ```
  Example: `balance addr1`

- **status** - Show the current status of the blockchain
  ```
  status
  ```

### Trading & Cross-Chain Operations

- **swap** - Exchange one token for another on the built-in DEX
  ```
  swap <token1> <token2> <amount>
  ```
  Example: `swap MARBLE USDC 5`

- **bridge** - Bridge tokens to or from other blockchains
  ```
  bridge <chain> <amount>
  ```
  Example: `bridge SOL 5`

### Validation & Consensus

- **validate** - Manually trigger the validation process (PoH+PoS)
  ```
  validate
  ```

## Features and Architecture

### Key Features

- **CLI-First Design**: Unlike other blockchains that treat CLI as an afterthought, Marble puts the command line at the center of the user experience.
- **High Performance**: Marble implements a hybrid PoH (Proof of History) and PoS (Proof of Stake) consensus mechanism inspired by Solana for high throughput and low latency.
- **Built-in DEX**: Native decentralized exchange functionality is integrated directly into the core protocol.
- **Cross-Chain Bridge**: Seamless interoperability with major blockchains like Solana, Ethereum, and BSC.
- **Developer-Friendly**: Clean architecture and well-documented code make it easy to build on top of Marble.

### Architecture

Marble Blockchain is built with a modular architecture:

- **Core Blockchain Layer**: Handles consensus, block creation, and state management (`marble_blockchain.py`)
- **CLI Interface**: Provides an interactive command line for blockchain operations (`marble_cli.py`)
- **API Layer**: RESTful API for programmatic access to blockchain functions (`marble_dex_app.py`)
- **UI Layer**: Web-based interface for non-technical users (future development)

### Consensus Mechanism

Marble implements a hybrid consensus mechanism:
- **Proof of History (PoH)**: Creates a historical record of events that makes it easier to verify the order of transactions
- **Proof of Stake (PoS)**: Validators stake tokens to participate in block production, with rewards proportional to stake size

## Future Plans

- **Full P2P Network Implementation**: Replace mock P2P with robust peer discovery and message propagation
- **Enhanced Web UI**: Develop a comprehensive dashboard for blockchain monitoring and interaction
- **Smart Contract Support**: Add VM for running Turing-complete smart contracts
- **Mobile Application**: Develop mobile clients for on-the-go blockchain interaction
- **Governance Framework**: Implement on-chain governance for protocol upgrades and parameter changes
- **Advanced DEX Features**: Limit orders, liquidity pools, and yield farming

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[MIT License](LICENSE)

# Marble Blockchain

## Overview

Marble Blockchain is a CLI-driven, high-performance blockchain platform aiming to match the capabilities of established networks like Solana, Ethereum, and BSC. This project focuses on delivering a powerful blockchain experience through a user-friendly command-line interface while maintaining the core features expected in modern blockchain systems.

The Marble Blockchain combines Proof of History (PoH) and Proof of Stake (PoS) consensus mechanisms, providing a fast and energy-efficient transaction validation system. Built with Python, it offers a complete blockchain solution with integrated DEX functionality accessible directly through the CLI.

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Required Python packages (install via pip):
  ```
  pip install cmd2 asyncio fastapi uvicorn
  ```

### Getting Started

1. Clone this repository:
   ```
   git clone https://github.com/your-username/marble-blockchain.git
   cd marble-blockchain
   ```

2. Run the CLI:
   ```
   python marble_cli.py
   ```

This will start the interactive Marble Blockchain CLI where you can enter commands to interact with the blockchain.

## CLI Commands

The Marble CLI provides the following commands:

| Command | Description | Example |
|---------|-------------|---------|
| `start_node` | Initialize blockchain with mock P2P networking | `start_node` |
| `send <sender> <recipient> <amount> <token>` | Create and add a new transaction to the blockchain | `send addr1 addr2 10 MARBLE` |
| `balance <address>` | Check the balance of a specific address | `balance addr1` |
| `swap <token1> <token2> <amount>` | Perform a token swap on the integrated DEX | `swap MARBLE USDT 10` |
| `bridge <chain> <amount>` | Execute a cross-chain bridge transaction | `bridge SOL 5` |
| `validate` | Trigger block validation using PoH+PoS | `validate` |
| `status` | Display blockchain status including chain length and node count | `status` |
| `exit` | Exit the CLI | `exit` |

### Example Session

```
Welcome to Marble Blockchain CLI!
Type 'help' for a list of commands.

marble> start_node
Node started at addr1
Connected to 3 nodes

marble> send addr1 addr2 10 MARBLE
Transaction added: addr1 sent 10 MARBLE to addr2

marble> balance addr1
{'MARBLE': 90, 'USDT': 1000}

marble> swap MARBLE USDT 5
Swapped 5 MARBLE to 25 USDT

marble> bridge SOL 5
Bridged 5 MARBLE to SOL

marble> validate
Block validated with PoH timestamp 14

marble> status
Chain length: 3 blocks
Connected nodes: 3
```

## Features

### Mock Proof of History (PoH) + Proof of Stake (PoS)

Marble Blockchain implements a simplified version of the PoH+PoS consensus mechanism:

- **Proof of History**: A verifiable delay function that creates a historical record of transactions, providing a time reference without requiring a centralized timestamp.
- **Proof of Stake**: A validator selection mechanism that weighs participants' chances of validating blocks according to their stake in the network.

### CLI-based DEX (Decentralized Exchange)

Unlike many blockchain platforms that separate core functionality from DEX features, Marble Blockchain integrates DEX capabilities directly into the CLI:

- Swap tokens with simple commands
- Bridge tokens across chains
- Check balances across multiple tokens

### Future Web UI Plans

While the current focus is on delivering a powerful CLI experience, we plan to develop a comprehensive web interface using Nuxt.js:

- Real-time blockchain explorer
- Wallet management
- Trading interface
- Staking dashboard
- Cross-chain bridge UI

## Project Structure

- `marble_blockchain.py`: Core blockchain implementation with PoH+PoS features
- `marble_cli.py`: Interactive CLI interface for blockchain interaction
- `marble_dex_app.py`: FastAPI implementation for web-based access (REST API)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

# Marble Blockchain

High-performance blockchain with DEX and cross-bridge support.

## Overview

Marble Blockchain is a modern blockchain implementation featuring a decentralized exchange (DEX) and cross-bridge support. It combines the speed and efficiency of Proof of History (PoH) with the security of Proof of Stake (PoS) consensus mechanisms. The platform includes a user-friendly UI built with Nuxt 3 and offers AI-powered block analysis capabilities.

## Setup Instructions

### Prerequisites

- Python 3.8+ 
- Node.js 16+
- npm 8+

### Backend Setup

1. Install required Python dependencies:
   ```bash
   pip install fastapi uvicorn pydantic aiohttp asyncio cmd2
   ```

2. Start the backend server:
   ```bash
   uvicorn marble_dex_app:app --port 8000
   ```

### Frontend Setup

1. Navigate to the UI directory:
   ```bash
   cd "C:\Users\Ultrabook Design i7\Desktop\marble-dex-ui"
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

The frontend will be available at http://localhost:3000

## CLI Documentation

Marble Blockchain includes a powerful command-line interface for interacting with the blockchain.

### Running the CLI

```bash
python marble_cli.py
```

### Available Commands

- `start` - Initialize the blockchain
- `send <address> <amount> <token>` - Send a transaction
- `balance <address>` - Check account balance
- `analyze <block_id>` - Get AI analysis of a specific block
- `validate <block_id> <coins>` - Validate a block and earn rewards
- `status` - Get current blockchain status
- `stake <amount>` - Stake tokens for participation in consensus
- `unstake <amount>` - Unstake previously staked tokens
- `help` - Display available commands and usage information
- `exit` - Exit the CLI

## Features

- **Hybrid Consensus**: Combines Proof of History (PoH) and Proof of Stake (PoS) for fast, secure validation
- **Decentralized Exchange**: Built-in DEX functionality with an intuitive UI
- **Cross-Chain Support**: Mock Solana bridge for interoperability
- **AI-Powered Analysis**: Advanced block and transaction analysis using AI
- **Interactive CLI**: Command-line interface for blockchain interaction
- **Modern Frontend**: Responsive UI built with Nuxt 3
- **Custom Branding**: Consistent Marble DEX visual identity
- **Transaction Management**: Simple interface for sending, receiving, and tracking transactions
- **Staking System**: Support for token staking and rewards

## Technologies Used

- **Backend**: FastAPI, Python, asyncio
- **Frontend**: Nuxt 3, Vue 3, TypeScript
- **Styling**: CSS with custom variables
- **AI Components**: Custom AI analysis modules
- **CLI**: Python cmd and asyncio
- **Blockchain Core**: Custom implementation with PoH and PoS

## API Endpoints

- `GET /status` - Get blockchain status
- `GET /blocks` - List all blocks
- `GET /transactions` - List all transactions
- `POST /trade` - Execute a trade
- `GET /bridge` - Mock Solana bridge
- `POST /validate_block` - Validate a block
- `GET /analyze_block/{block_id}` - Get AI analysis of a specific block
- `GET /dex_config` - Get DEX configuration

# Marble Blockchain

A high-performance blockchain platform with integrated DEX (Decentralized Exchange) and cross-bridge support.

## Project Overview

Marble Blockchain is an advanced blockchain implementation featuring:

- **Proof of History (PoH) + Proof of Stake (PoS)** consensus mechanism
- **Integrated DEX** with Raydium V3-based UI
- **Mock Solana Bridge** for cross-chain interoperability
- **AI-powered block analysis** for enhanced security and insights
- **Interactive CLI** with powerful management commands
- **FastAPI Backend** for seamless integration between components

The project combines the speed and reliability of modern blockchain technology with user-friendly interfaces and advanced analytical capabilities.

## Setup Instructions

### Prerequisites

- Python 3.8+ with pip
- Node.js and npm
- Git (optional for version control)

### Backend Setup

1. Install required Python packages:
   ```bash
   pip install fastapi uvicorn aiohttp asyncio pydantic python-multipart
   ```

2. Start the backend server:
   ```bash
   uvicorn marble_dex_app:app --port 8000 --reload
   ```

### Frontend Setup

1. Navigate to the DEX UI directory:
   ```bash
   cd "C:\Users\Ultrabook Design i7\Desktop\marble-dex-ui"
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the frontend application:
   ```bash
   npm start
   ```

The frontend will be available at http://localhost:3000 and will connect to the backend running on http://localhost:8000.

## CLI Usage

Run the CLI by executing:
```bash
python marble_cli.py
```

This will start an interactive shell with the following commands:

| Command | Description | Example |
|---------|-------------|---------|
| `start` | Initialize blockchain and P2P node | `start` |
| `send <address> <amount> <token>` | Create a new transaction | `send 0x123 10 MARBLE` |
| `balance <address>` | Check balance of an address | `balance 0x123` |
| `analyze <block_id>` | Perform AI analysis on a block | `analyze 42` |
| `validate <block_id> <coins>` | Validate a block with stake | `validate 42 10` |
| `status` | Check blockchain status | `status` |
| `stake <amount>` | Stake coins for validation | `stake 100` |
| `unstake <amount>` | Remove staked coins | `unstake 50` |
| `exit` | Exit the CLI | `exit` |

### Example CLI Session

```
> start
Blockchain initialized. P2P mock node started.

> balance 0x123abc
Address 0x123abc has balance: {'MARBLE': 100, 'USDC': 500}

> send 0xdef456 25 MARBLE
Transaction added to pool. Will be included in next block.

> stake 50
Staked 50 MARBLE coins. Current stake: 50 MARBLE.

> validate 7 10
Block 7 validated with 10 coins stake. Reward: 0.5 MARBLE.
```

## Features

### Blockchain

- **PoH+PoS Consensus**: Combines the efficiency of Proof of History with the energy efficiency of Proof of Stake
- **Transaction System**: Fast and secure transaction processing with multi-token support
- **Block Validation**: Decentralized validation mechanism with staking rewards
- **Mock P2P Network**: Simulated peer-to-peer networking (to be expanded in future versions)

### DEX (Decentralized Exchange)

- **Swap Interface**: Token swap functionality with competitive fees
- **Liquidity Pools**: Add and remove liquidity from trading pairs
- **Price Charts**: Real-time price monitoring and historical data
- **Wallet Integration**: Connect with various wallet providers

### Bridge

- **Mock Solana Bridge**: Simulated cross-chain transfers between Marble and Solana
- **Token Wrapping**: Mock wrapping of tokens for cross-chain compatibility

### AI Analysis

- **Block Analysis**: AI-powered analysis of block content and transaction patterns
- **Anomaly Detection**: Identify suspicious activities and potential security threats
- **Performance Optimization**: Suggestions for improving blockchain efficiency

## Development Guidelines

### Project Structure

- `marble_dex_app.py`: FastAPI backend handling HTTP endpoints
- `marble_blockchain.py`: Core blockchain implementation
- `RegenerativeDeepSeekAI.py`: AI analysis module
- `marble_cli.py`: Interactive command-line interface
- Frontend: Modified Raydium V3 interface with Marble branding

### Contributing

1. Follow the existing code style and patterns
2. Write tests for new functionality
3. Update documentation when adding features
4. Use meaningful commit messages

### Future Development

- Full P2P network implementation
- Expanded AI capabilities
- Real bridge to Solana and other chains
- Mobile app integration
- Enhanced security features

## License

This project is licensed under the MIT License - see the LICENSE file for details.

# Marble Blockchain

![Marble DEX Logo](path/to/logo.png)

## Project Overview

Marble Blockchain is a high-performance blockchain platform with integrated DEX (Decentralized Exchange) capabilities and cross-bridge support. Built with a unique combination of Proof of History (PoH) and Proof of Stake (PoS) consensus mechanisms, it offers fast transaction processing, enhanced security, and a seamless trading experience.

The project consists of a Python-based blockchain implementation, a FastAPI backend service, an interactive CLI, and a React-based DEX UI. It also includes advanced features such as AI-powered block analysis and mock Solana bridge functionality.

## Setup Instructions

### Prerequisites

- Python 3.8+
- Node.js 14+
- npm 6+

### Backend Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/marble-blockchain.git
   cd marble-blockchain
   ```

2. Create and activate a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install Python dependencies:
   ```bash
   pip install fastapi uvicorn aiohttp asyncio pydantic python-dotenv
   ```

4. Start the FastAPI backend:
   ```bash
   uvicorn marble_dex_app:app --port 8000 --reload
   ```

### Frontend Setup

1. Navigate to the DEX UI directory:
   ```bash
   cd "C:\Users\Ultrabook Design i7\Desktop\marble-dex-ui"
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the frontend development server:
   ```bash
   npm start
   ```

4. Access the DEX UI at `http://localhost:3000`

## CLI Usage Documentation

The Marble CLI provides an interactive shell for interacting with the blockchain. It allows you to initialize the blockchain, send transactions, check balances, analyze blocks, and more.

### Starting the CLI

```bash
python marble_cli.py
```

### Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `start` | Initialize blockchain and P2P node | `start` |
| `send <address> <amount> <token>` | Send tokens to an address | `send marble1abc123 10 MARBLE` |
| `balance <address>` | Check balance of an address | `balance marble1abc123` |
| `analyze <block_id>` | Analyze a specific block using AI | `analyze 42` |
| `validate <block_id> <coins>` | Validate a block with staked coins | `validate 42 10` |
| `status` | Check blockchain status | `status` |
| `stake <amount>` | Stake tokens for validation | `stake 100` |
| `unstake <amount>` | Unstake tokens | `unstake 50` |
| `help` | Display available commands | `help` |
| `quit` | Exit the CLI | `quit` |

### Examples

```
> start
Initializing Marble blockchain...
Blockchain started successfully.

> send marble1xyz789 25 MARBLE
Transaction added to the pool.
Transaction will be included in the next block.

> balance marble1xyz789
Address: marble1xyz789
Balance: {"MARBLE": 125, "USDC": 500}

> analyze 3
AI Analysis of Block #3:
- 5 transactions processed
- No anomalies detected
- Average transaction amount: 12.3 MARBLE
```

## Features

### Core Blockchain

- **Hybrid PoH+PoS Consensus**: Combines the efficiency of Proof of History with the energy efficiency of Proof of Stake
- **Transaction Processing**: Fast and efficient transaction validation and processing
- **Multi-token Support**: Native support for multiple token types

### DEX UI

- **Swap Interface**: User-friendly token swapping interface
- **Price Charts**: Real-time price tracking and historical data
- **Liquidity Pools**: Support for creating and managing liquidity pools
- **Wallet Integration**: Seamless wallet connection

### Bridge Functionality

- **Mock Solana Bridge**: Simulated cross-chain bridge with Solana
- **Token Wrapping**: Virtual representation of cross-chain assets

### Advanced Analytics

- **AI-Powered Block Analysis**: Deep learning-based analysis of blockchain activity
- **Anomaly Detection**: Identification of unusual transaction patterns
- **Performance Metrics**: Real-time blockchain performance monitoring

### Developer Tools

- **Interactive CLI**: Command-line interface for blockchain interaction
- **API Endpoints**: Comprehensive API for application integration
- **Parallel Validation**: Multi-threaded block validation

## Development Guidelines and Structure

### Project Structure

```
marble-blockchain/
├── marble_blockchain.py    # Core blockchain implementation
├── marble_dex_app.py       # FastAPI backend service
├── marble_cli.py           # Interactive CLI
├── RegenerativeDeepSeekAI.py  # AI analysis module
└── docs/                   # Documentation
```

```
marble-dex-ui/
├── public/                 # Static assets
├── src/
│   ├── assets/             # Images and media
│   ├── components/         # React components
│   ├── utils/              # Utility functions
│   ├── App.tsx             # Main application component
│   └── index.tsx           # Entry point
└── package.json            # Dependencies and scripts
```

### Development Workflow

1. **Feature Development**:
   - Create a feature branch from `main`
   - Implement and test your changes
   - Submit a pull request for review

2. **Testing**:
   - Write unit tests for new features
   - Run the test suite before submitting changes
   - Ensure compatibility with existing features

3. **Code Style**:
   - Follow PEP 8 guidelines for Python code
   - Use ESLint and Prettier for JavaScript/TypeScript
   - Document functions and complex logic

4. **API Changes**:
   - Update API documentation when endpoints change
   - Maintain backward compatibility when possible
   - Version major API changes

### Contributing

Contributions to Marble Blockchain are welcome! Please see our [Contributing Guide](CONTRIBUTING.md) for more information on how to get involved.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

# Marble Blockchain

## Project Overview

Marble Blockchain is a modern hybrid Proof of History (PoH) + Proof of Stake (PoS) blockchain platform with integrated DEX (Decentralized Exchange) functionality. The platform combines the verifiable delay functions of PoH with the energy efficiency of PoS to create a high-performance, secure, and scalable blockchain solution.

### Key Features

- **Hybrid PoH+PoS Consensus**: Combines Proof of History for verifiable time and sequencing with Proof of Stake for validator selection
- **High Performance**: Capable of processing thousands of transactions per second
- **Secure Wallet Management**: HD wallet support with BIP39 mnemonic seed phrases
- **Integrated DEX**: Built-in decentralized exchange functionality
- **P2P Network**: Robust peer-to-peer networking with automatic node discovery
- **Smart Contract Support**: Framework for deploying and executing smart contracts
- **Multi-token Support**: Native support for multiple token types and custom tokens

## Architecture

The Marble Blockchain architecture consists of several core components:

1. **Core Blockchain Module** (`marble_blockchain.py`):
   - Implements the main blockchain logic, consensus mechanism, and state management
   - Handles block production and validation
   - Manages the distributed ledger

2. **DEX Component** (`marble_dex_app.py`):
   - Provides APIs for token swaps, liquidity pools, and trading
   - Integrates with the Raydium V3 frontend
   - Supports analysis and validation of blockchain transactions

3. **CLI Interface** (`marble_cli.py`):
   - Interactive command-line interface for blockchain interaction
   - Support for wallet management, transactions, and blockchain queries
   - Direct integration with the DEX functionality

4. **Frontend UI** (Raydium V3 based):
   - Web-based interface for interacting with the Marble DEX
   - Customized Raydium UI with Marble branding
   - Advanced features for blockchain analysis and validation

### Data Flow

```
User → CLI/UI → Marble Blockchain Core → P2P Network → Validator Nodes
     ↓                  ↑
     → DEX Component ←
```

## Consensus Mechanism

Marble Blockchain employs a hybrid consensus mechanism combining Proof of History (PoH) and Proof of Stake (PoS):

### Proof of History (PoH)

PoH is a high-frequency Verifiable Delay Function (VDF) that creates a historical record proving that data existed at a specific moment in time. Key aspects:

- Creates a sequential hash chain using SHA-256
- Each hash incorporates the previous hash, creating a verifiable sequence
- Provides a cryptographically secure clock for the network
- Enables parallel validation of transactions
- Timestamps transactions in a tamper-proof manner

### Proof of Stake (PoS)

PoS selects validators proportionally to their stake in the network. Key aspects:

- Validators stake MARBLE tokens as collateral
- Validator selection weighted by stake amount
- Energy-efficient alternative to Proof of Work
- Economic incentives for honest validation
- Slashing conditions for malicious behavior

### Hybrid Integration

The hybrid approach works as follows:

1. PoH maintains a verifiable sequence of events and timestamps
2. PoS selects validators for block production and confirmation
3. The leader (block producer) for each slot is selected by PoS
4. Transactions are ordered and timestamped by PoH
5. Validators confirm the PoH sequence and transaction validity
6. The network reaches consensus on the global state

This hybrid model delivers high throughput, fast finality, and strong security with minimal energy consumption.

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Required Python packages: aiohttp, ed25519, cryptography, fastapi, uvicorn, requests, secp256k1, mnemonic, bip32utils
- 4GB RAM minimum (8GB recommended)
- 50GB storage space for blockchain data
- Stable internet connection for P2P networking

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/marble-blockchain/marble-core.git
   cd marble-core
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create required directories:
   ```
   mkdir -p ~/.marble/wallets ~/.marble/chaindata ~/.marble/logs
   ```

4. Initialize the blockchain:
   ```
   python marble_blockchain.py --init
   ```

### Running a Node

#### Regular Node

To run a standard non-validator node:

```
python marble_blockchain.py --network mainnet
```

#### Validator Node

To run a validator node:

1. Generate a validator key:
   ```
   python marble_blockchain.py --generate-validator-key
   ```

2. Start the validator:
   ```
   python marble_blockchain.py --validator --key-path ~/.marble/validator_key.pem
   ```

3. Stake tokens to activate your validator:
   ```
   python marble_cli.py stake --amount 1000 --validator [VALIDATOR_ADDRESS]
   ```

### Starting the DEX

To run the DEX component:

```
python marble_dex_app.py
```

## Usage Examples

### CLI Examples

#### Wallet Management

Create a new wallet:
```
python marble_cli.py create-wallet
```

Check wallet balance:
```
python marble_cli.py balance --address 0x123abc...
```

Import wallet from seed phrase:
```
python marble_cli.py import-wallet
```

#### Transactions

Send tokens:
```
python marble_cli.py send --recipient 0x456def... --amount 10 --token MARBLE
```

Stake tokens:
```
python marble_cli.py stake --amount 100
```

Unstake tokens:
```
python marble_cli.py unstake --amount 50
```

#### Blockchain Information

Show blockchain status:
```
python marble_cli.py status
```

Analyze a block:
```
python marble_cli.py analyze --block-id 1234
```

Validate a block:
```
python marble_cli.py validate --block-id 1234 --coins 5
```

### API Examples

#### DEX API

Get DEX status:
```
curl -X GET http://localhost:8000/status
```

Get DEX configuration:
```
curl -X GET http://localhost:8000/dex_config
```

Analyze a block:
```
curl -X GET http://localhost:8000/analyze_block/1234
```

Validate a block:
```
curl -X POST http://localhost:8000/validate_block \
  -H "Content-Type: application/json" \
  -d '{"block_id": 1234, "compute_coins": 5}'
```

## Development Guidelines

### Coding Standards

- Follow PEP 8 style guide for Python code
- Use type hints for function parameters and return values
- Document classes and functions with docstrings
- Write unit tests for all new functionality
- Use async/await for I/O-bound operations

### Git Workflow

1. Create feature branches from `develop`
2. Use descriptive commit messages
3. Submit pull requests with detailed descriptions
4. Ensure CI tests pass before merging
5. Releases are tagged from the `main` branch

### Testing

Run unit tests:
```
pytest tests/
```

Run integration tests:
```
pytest tests/integration/ --network testnet
```

### Documentation

Update documentation for any API changes:
```
cd docs && make html
```

## License

Marble Blockchain is released under the MIT License. See LICENSE file for details.

## Contact

- Website: https://
- Discord: https://
- Twitter: [@MarbleCeo](https://x.com/MarbleCeo)
- Email: marbleblockchain@gmail.com