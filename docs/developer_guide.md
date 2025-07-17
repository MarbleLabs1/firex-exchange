# DEX Blockchain Project - Developer Guide

## Architecture Overview

The DEX Blockchain project follows a modular architecture with clear separation of concerns:

- **Frontend**: PyQt6-based GUI providing trading interface and wallet management
- **Backend**: Python services handling trading logic, market making, and analytics
- **Blockchain**: Core services for blockchain interaction, particularly with Solana
- **Security**: Authentication and encryption modules
- **Utils**: Shared utilities for logging, error handling, and monitoring

## Development Environment Setup

```bash
# Clone the repository (for future contributors)
# git clone [repository-url]

# Navigate to project directory
cd DEX

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1  # On Windows PowerShell

# Install dependencies
pip install -r requirements.txt
```

## Module Structure

### Frontend

The frontend is built with PyQt6 and includes:

- `main_window.py`: Main application window with tabs for Swap, Pools, Charts, and Wallet
- `styles.qss`: Qt StyleSheet for UI theming
- UI components in subdirectories

### Blockchain Core

- `blockchain_core.py`: Primary interface for blockchain interactions
- `solana_client.py`: Solana blockchain client implementation
- `blockchain_mirror.py`: Local mirror of blockchain state for faster lookups

### Trading Services

- `dex_trading.py`: Core trading engine for the DEX
- `market_maker.py`: Automated market making algorithms
- `dex_analytics.py`: Trading analytics and insights

### Security

- `authentication.py`: User authentication services
- `encryption.py`: Data encryption utilities

## Adding New Features

1. Create feature branch from main
2. Implement feature following project architecture
3. Write appropriate unit tests
4. Document the feature
5. Submit pull request

## Testing

The project uses pytest for testing:

```bash
python -m pytest tests/
```

## Logging

The application uses Python's logging module, configured in `config/logging_config.py`.

## Configuration

Application configuration is managed through:
- Environment variables (via .env file)
- Configuration modules in the config directory

## Deployment

See `deployment_guide.md` for Docker-based deployment instructions.

