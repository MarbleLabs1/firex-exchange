import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
LOGS_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"

# Create necessary directories if they don't exist
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Blockchain settings
BLOCKCHAIN_NETWORK = os.getenv("BLOCKCHAIN_NETWORK", "testnet")
RPC_URL = os.getenv("RPC_URL", "http://localhost:8545")
CHAIN_ID = int(os.getenv("CHAIN_ID", "1337"))

# Database settings
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///" + str(BASE_DIR / "dex.db"))

# API settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_DEBUG = os.getenv("API_DEBUG", "False").lower() in ("true", "1", "t")

# Security settings
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-for-development-only")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# GUI settings
GUI_THEME = os.getenv("GUI_THEME", "dark")
GUI_STYLE = os.getenv("GUI_STYLE", "modern")

# DEX settings
DEX_NAME = os.getenv("DEX_NAME", "PyDEX")
DEX_VERSION = os.getenv("DEX_VERSION", "1.0.0")
DEX_FEE_PERCENTAGE = float(os.getenv("DEX_FEE_PERCENTAGE", "0.3"))  # 0.3%
LIQUIDITY_PROVIDER_FEE = float(os.getenv("LIQUIDITY_PROVIDER_FEE", "0.25"))  # 0.25%

# Trading settings
MAX_SLIPPAGE = float(os.getenv("MAX_SLIPPAGE", "0.5"))  # 0.5%
DEFAULT_GAS_LIMIT = int(os.getenv("DEFAULT_GAS_LIMIT", "300000"))
GAS_PRICE_STRATEGY = os.getenv("GAS_PRICE_STRATEGY", "medium")  # slow, medium, fast

# Logging settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

