import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Solana RPC Configuration
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
SOLANA_WS_URL = os.getenv("SOLANA_WS_URL", "wss://api.mainnet-beta.solana.com")

# Program IDs
DEX_PROGRAM_ID = os.getenv("DEX_PROGRAM_ID", "")  # Your DEX program ID
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"  # Solana Token Program
SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"  # Solana System Program

# Network Configuration
NETWORK = os.getenv("SOLANA_NETWORK", "mainnet-beta")  # mainnet-beta, testnet, or devnet

# Transaction Configuration
MAX_RETRIES = 3
CONFIRMATION_TIMEOUT = 30  # seconds

# Cache Configuration
CACHE_DURATION = 60  # seconds
MAX_CACHE_SIZE = 1000  # items

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = "logs/solana.log" 