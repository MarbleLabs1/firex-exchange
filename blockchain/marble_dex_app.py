import sys
import os
import json
import time
import logging
import random
import asyncio
import io
import base64
import hmac
import hashlib
import uuid
import re
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime, timedelta
from enum import Enum
from contextlib import asynccontextmanager

# FastAPI imports
from fastapi import FastAPI, Depends, HTTPException, WebSocket, Request, status, BackgroundTasks, Body, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.websockets import WebSocket, WebSocketDisconnect
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from pydantic import BaseModel, Field, field_validator, validator

# Data analysis and visualization
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use the 'Agg' backend which doesn't require a display
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.patches as patches

# System monitoring
import psutil

# Custom modules
import microos
from marble_blockchain import MarbleBlockchain, SecurityManager, Transaction, TransactionType, ExternalIntegrationError, NetworkMode

#----------------------------------------------
# Configure logging
#----------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("marble_dex.log")
    ]
)
logger = logging.getLogger("marble_dex")

#----------------------------------------------
# Constants and configuration
#----------------------------------------------
MIN_AMOUNT = 0.000001
MAX_AMOUNT = 1_000_000_000
RAYDIUM_UI_PATH = r"C:\Users\Ultrabook Design i7\Desktop\marble-dex-ui"
DEX_CONFIG_FILE = "dex_config.json"
ADMIN_TOKEN = "your-admin-token"  # In production, use environment variable

# API configuration
API_RATE_LIMIT = 60  # Requests per minute
API_CORS_ORIGINS = ["http://localhost:8000"]

# Configure security
security = HTTPBearer()

# Mock data stores
connected_websocket_clients = set()
order_book_data = {
    "bids": [
        {"price": 15.5, "amount": 10.0, "total": 155.0},
        {"price": 15.2, "amount": 5.0, "total": 76.0},
        {"price": 15.0, "amount": 20.0, "total": 300.0},
        {"price": 14.8, "amount": 15.0, "total": 222.0},
        {"price": 14.5, "amount": 8.0, "total": 116.0},
    ],
    "asks": [
        {"price": 16.0, "amount": 12.0, "total": 192.0},
        {"price": 16.2, "amount": 8.0, "total": 129.6},
        {"price": 16.5, "amount": 5.0, "total": 82.5},
        {"price": 16.8, "amount": 3.0, "total": 50.4},
        {"price": 17.0, "amount": 10.0, "total": 170.0},
    ],
    "last_updated": datetime.now().isoformat()
}

# Mock user tokens (replace with a proper database in production)
API_TOKENS = {
    "test-user": "5f4dcc3b5aa765d61d8327deb882cf99",  # This is a placeholder, in production use proper secure tokens
}

# Mock wallet addresses (replace with real verification in production)
valid_wallet_addresses = [
    "wallet_address_1",
    "wallet_address_2",
    "wallet_address_3",
    "wallet_address_4",
]

# Mock locked tokens (replace with blockchain storage in production)
locked_tokens = {}

#----------------------------------------------
# Helper Classes and Functions
#----------------------------------------------

# Rate limiting middleware
class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute=60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_log = {}
        
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        current_time = time.time()
        
        # Clean up old requests
        self.request_log = {ip: requests for ip, requests in self.request_log.items() 
                           if current_time - requests[-1] < 60}
        
        # Check rate limit
        if client_ip in self.request_log:
            requests = self.request_log[client_ip]
            if len(requests) >= self.requests_per_minute:
                if current_time - requests[0] < 60:
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={"detail": "Rate limit exceeded. Please try again later."}
                    )
                else:
                    # Remove older requests
                    self.request_log[client_ip] = [req for req in requests if current_time - req < 60]
            
            # Add current request
            self.request_log[client_ip].append(current_time)
        else:
            # First request from this IP
            self.request_log[client_ip] = [current_time]
            
        # Process the request
        return await call_next(request)

# WebSocket manager for order book updates
class OrderBookManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.last_update = {}
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        
    async def broadcast_orderbook(self, data: dict):
        self.last_update = data
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except:
                continue

# Create a global order book manager instance
orderbook_manager = OrderBookManager()
# Rate limiter for API requests
class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.time_window = 60  # 1 minute in seconds
        self.request_times: Dict[str, List[float]] = {}
        
    async def check_rate_limit(self, ip: str) -> bool:
        current_time = time.time()
        if ip not in self.request_times:
            self.request_times[ip] = []
            
        # Remove old requests
        self.request_times[ip] = [t for t in self.request_times[ip] 
                                if current_time - t < self.time_window]
                                
        if len(self.request_times[ip]) >= self.requests_per_minute:
            return False
            
        self.request_times[ip].append(current_time)
        return True

# Create a global rate limiter instance
rate_limiter = RateLimiter(API_RATE_LIMIT)

# WebSocket connection manager for order book updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.last_orderbook = order_book_data  # Initialize with default data

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total connections: {len(self.active_connections)}")
        
        # Send the current order book data to the new client
        await websocket.send_json(self.last_orderbook)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        self.last_orderbook = message
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to WebSocket client: {e}")
                # The connection might be closed, but we'll handle that in the main WebSocket route

# Create a global connection manager
manager = ConnectionManager()
rate_limiter = RateLimiter()

# Authentication functions
async def verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != ADMIN_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Invalid admin token"
        )
    return credentials.credentials

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    
    # In a real implementation, validate against a secure database
    # This is a simplified example
    for user, user_token in API_TOKENS.items():
        if hmac.compare_digest(token, user_token):
            return user
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

# Rate limiting dependency
async def check_rate_limit(request: Request):
    client_ip = request.client.host
    is_allowed = await rate_limiter.check_rate_limit(client_ip)
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )
    return True

# DEX helper functions
def verify_dex_path_exists() -> bool:
    """
    Verifies that the Raydium UI path exists.
    
    Returns:
        bool: True if the path exists, False otherwise.
    """
    exists = os.path.exists(RAYDIUM_UI_PATH)
    if not exists:
        logger.error(f"DEX path does not exist: {RAYDIUM_UI_PATH}")
    return exists

def load_dex_config() -> Dict[str, Any]:
    """
    Loads the DEX configuration from the config file.
    
    Returns:
        Dict[str, Any]: The DEX configuration.
    """
    if not verify_dex_path_exists():
        return {}
    
    config_path = os.path.join(RAYDIUM_UI_PATH, DEX_CONFIG_FILE)
    
    # If the config file doesn't exist, create a default one
    if not os.path.exists(config_path):
        default_config = {
            "tokens": {},
            "pairs": {},
            "pools": {},
            "last_updated": None
        }
        try:
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            logger.info(f"Created default DEX config at {config_path}")
            return default_config
        except Exception as e:
            logger.error(f"Failed to create default DEX config: {str(e)}")
            return {}
    
    # Read the existing config file
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        logger.info(f"Loaded DEX config from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Failed to load DEX config: {str(e)}")
        return {}

def read_dex_file(relative_path: str) -> Dict[str, Any]:
    """
    Reads a file from the Raydium UI directory.
    
    Args:
        relative_path (str): The relative path to the file.
        
    Returns:
        Dict[str, Any]: The content of the file as a dictionary, or empty dict if file doesn't exist.
    """
    if not verify_dex_path_exists():
        return {}
    
    file_path = os.path.join(RAYDIUM_UI_PATH, relative_path)
    
    if not os.path.exists(file_path):
        logger.warning(f"File does not exist: {file_path}")
        return {}
    
    try:
        with open(file_path, 'r') as f:
            content = json.load(f)
        logger.info(f"Successfully read file: {file_path}")
        return content
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {str(e)}")
        return {}

def get_token_list() -> List[Dict[str, Any]]:
    """
    Retrieves the list of tokens available in the DEX.
    
    Returns:
        List[Dict[str, Any]]: A list of token information.
    """
    # Typically token lists might be in a src/constants or public directory
    potential_paths = [
        "src/constants/tokens.json",
        "public/tokens.json", 
        "src/data/tokens.json"
    ]
    
    for path in potential_paths:
        tokens = read_dex_file(path)
        if tokens:
            return tokens.get("tokens", []) if isinstance(tokens, dict) else tokens
    
    logger.warning("Could not find token list in Raydium UI directory")
    return []

def get_pool_info(pool_id: str) -> Dict[str, Any]:
    """
    Gets information about a specific liquidity pool.
    
    Args:
        pool_id (str): The ID of the pool.
        
    Returns:
        Dict[str, Any]: Pool information.
    """
    config = load_dex_config()
    return config.get("pools", {}).get(pool_id, {})

# DEX API Models
class TradeRequest(BaseModel):
    pair: str = Field(..., description="Trading pair (e.g., MARBLE/USDT)")
    price: float = Field(..., ge=0.000001, description="Price per token")
    amount: float = Field(..., ge=0.000001, description="Amount of tokens to trade")
    type: str = Field(..., description="Order type (buy or sell)")
    
    @field_validator("pair")
    def validate_pair(cls, value):
        if not re.match(r'^[A-Z]+/[A-Z]+$', value):
            raise ValueError("Invalid trading pair format. Must be TOKEN1/TOKEN2")
        return value
    
    @field_validator("type")
    def validate_type(cls, value):
        if value.lower() not in ["buy", "sell"]:
            raise ValueError("Order type must be 'buy' or 'sell'")
        return value.lower()

class LockTokensRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount of tokens to lock")
    duration_days: int = Field(365, ge=30, description="Lock duration in days")

# Background tasks
async def update_orderbook():
    """Background task to update the order book periodically."""
    while True:
        try:
            # In a real implementation, this would fetch data from an exchange or database
            # Here we just add some random variation to simulate changes
            updated_order_book = {
                "bids": [
                    {"price": 15.5 + random.uniform(-0.1, 0.1), "amount": 10.0 + random.uniform(-1, 1), "total": 155.0},
                    {"price": 15.2 + random.uniform(-0.1, 0.1), "amount": 5.0 + random.uniform(-0.5, 0.5), "total": 76.0},
                    {"price": 15.0 + random.uniform(-0.1, 0.1), "amount": 20.0 + random.uniform(-2, 2), "total": 300.0},
                    {"price": 14.8 + random.uniform(-0.1, 0.1), "amount": 15.0 + random.uniform(-1.5, 1.5), "total": 222.0},
                    {"price": 14.5 + random.uniform(-0.1, 0.1), "amount": 8.0 + random.uniform(-0.8, 0.8), "total": 116.0},
                ],
                "asks": [
                    {"price": 16.0 + random.uniform(-0.1, 0.1), "amount": 12.0 + random.uniform(-1.2, 1.2), "total": 192.0},
                    {"price": 16.2 + random.uniform(-0.1, 0.1), "amount": 8.0 + random.uniform(-0.8, 0.8), "total": 129.6},
                    {"price": 16.5 + random.uniform(-0.1, 0.1), "amount": 5.0 + random.uniform(-0.5, 0.5), "total": 82.5},
                    {"price": 16.8 + random.uniform(-0.1, 0.1), "amount": 3.0 + random.uniform(-0.3, 0.3), "total": 50.4},
                    {"price": 17.0 + random.uniform(-0.1, 0.1), "amount": 10.0 + random.uniform(-1, 1), "total": 170.0},
                ],
                "last_updated": datetime.now().isoformat()
            }
            
            # Recalculate totals
            for side in ["bids", "asks"]:
                for item in updated_order_book[side]:
                    item["total"] = item["price"] * item["amount"]
            
            # Broadcast to all connected clients
            await manager.broadcast(updated_order_book)
            
            # Wait before the next update
            await asyncio.sleep(2)  # Update every 2 seconds
        except Exception as e:
            logger.error(f"Error in update_orderbook task: {e}")
            await asyncio.sleep(5)  # Wait longer on error

def generate_price_chart(pair: str = "MARBLE/USDT", timeframe: str = "1h", periods: int = 24):
    """
    Generate a price chart for a trading pair
    
    Args:
        pair: The trading pair (e.g., 'MARBLE/USDT')
        timeframe: Time period for each candle (e.g., '1h', '1d')
        periods: Number of candles to generate
        
    Returns:
        BytesIO object containing the chart image
    """
    # Create a DataFrame with timestamps
    timestamps = [datetime.now() - timedelta(hours=i) for i in range(periods, 0, -1)]
    df = pd.DataFrame({'timestamp': timestamps})
    df = df.set_index('timestamp')
    
    # Generate mock price data
    base_price = 15.0
    trend = np.linspace(0, 1, periods) * 2 - 1  # -1 to 1 trend
    volatility = np.random.normal(0, 0.5, periods)  # Random noise
    
    # Add columns to the dataframe
    df['close'] = base_price + base_price * (0.1 * trend + 0.05 * volatility)
    
    # Create open, high, low values
    df['open'] = df['close'].shift(1)
    df.loc[df.index[0], 'open'] = df['close'].iloc[0] * (1 - 0.01 * np.random.rand())  # First open value
    
    # Generate high and low values
    df['high'] = df[['open', 'close']].max(axis=1) + abs(np.random.normal(0, 0.1, len(df)))
    df['low'] = df[['open', 'close']].min(axis=1) - abs(np.random.normal(0, 0.1, len(df)))
    
    # Create the plot
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Set the plot background color
    fig.patch.set_facecolor('#1A1A1A')
    ax.set_facecolor('#1A1A1A')
    
    # Plot the candlestick chart
    for i, (idx, row) in enumerate(df.iterrows()):
        # Determine candle color (green for up, red for down)
        if row['close'] >= row['open']:
            color = '#00FF00'  # Green for up
            body_bottom = row['open']
            body_height = row['close'] - row['open']
        else:
            color = '#FF0000'  # Red for down
            body_bottom = row['close']
            body_height = row['open'] - row['close']
        
        # Plot the candlestick
        # Body
        ax.add_patch(
            patches.Rectangle(
                (i - 0.4, body_bottom),  # (x, y)
                0.8,  # width
                body_height,  # height
                color=color,
                alpha=0.8,
            )
        )
        
        # Wicks
        plt.plot([i, i], [row['low'], row['high']], color='white', linewidth=1)
    
    # Format the plot
    plt.title(f"{pair} - {timeframe} Chart", color='white', fontsize=16)
    plt.xlabel("Time", color='white')
    plt.ylabel("Price", color='white')
    
    # Format the axis
    ax.tick_params(colors='white')
    ax.spines['bottom'].set_color('white')
    ax.spines['top'].set_color('white')
    ax.spines['left'].set_color('white')
    ax.spines['right'].set_color('white')
    
    # Set x-axis labels
    plt.xticks(range(len(df)), [idx.strftime('%H:%M' if timeframe == '1h' else '%d-%m') for idx in df.index], 
              rotation=45)
    
    plt.tight_layout()
    
    # Save the figure to a BytesIO object
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    plt.close(fig)
    
    # Reset the buffer position to the beginning
    buf.seek(0)
    return buf

# Initialize blockchain and other components
blockchain = None

# Startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize blockchain and generate icons
    global blockchain
    logger.info("Starting Marble Blockchain DEX...")
    
    # Initialize blockchain with standalone mode and local network configuration
    blockchain = MarbleBlockchain(
        network_mode=NetworkMode.LOCAL,
        host="127.0.0.1",
        port=9090,
        standalone_mode=True  # Enable standalone mode to work without peer connections
    )
    logger.info("Initializing blockchain in standalone mode...")
    await blockchain.start()
    
    # Generate VMIA icons
    logger.info("Generating VMIA icons...")
    microos.generate_icon("swap")
    microos.generate_icon("lock")
    
    # Start background task to update orderbook
    asyncio.create_task(update_orderbook())
    
    # Test VMIA task
    asyncio.create_task(blockchain.run_vmia_task("your-address-123", "swap"))
    
    logger.info("Blockchain started in standalone mode - no peer connections required")
    
    yield
    
    # Shutdown: cleanup resources
    logger.info("Shutting down Marble Blockchain DEX...")
    if blockchain:
        await blockchain.stop()

# Create FastAPI application
app = FastAPI(
    title="Marble Blockchain DEX",
    description="Decentralized Exchange for Marble Blockchain",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="templates")

# Add middleware
app.add_middleware(RateLimitMiddleware, requests_per_minute=API_RATE_LIMIT)
app.add_middleware(
    CORSMiddleware,
    allow_origins=API_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#----------------------------------------------
# API Routes
#----------------------------------------------

# DEX WebUI
@app.get("/", response_class=HTMLResponse)
async def dex_root(request: Request):
    """
    Serve the DEX WebUI
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/trade")
async def trade(
    data: TradeRequest,
    _: bool = Depends(check_rate_limit)
):
    """
    Execute a trade order
    """
    try:
        pair = data.pair
        price = data.price
        amount = data.amount
        order_type = data.type
        
        # In a real implementation, this would interact with the blockchain
        # For this demo, we generate a random tx_hash
        tx_hash = hashlib.sha256(f"{pair}{price}{amount}{order_type}{time.time()}".encode()).hexdigest()
        
        # Update orderbook (mock)
        if order_type == "buy":
            order_book_data["bids"].insert(0, {
                "price": price,
                "amount": amount,
                "total": price * amount,
                "tx_hash": tx_hash
            })
            # Sort bids descending
            order_book_data["bids"] = sorted(order_book_data["bids"], key=lambda x: x["price"], reverse=True)
        else:
            order_book_data["asks"].insert(0, {
                "price": price,
                "amount": amount,
                "total": price * amount,
                "tx_hash": tx_hash
            })
            # Sort asks ascending
            order_book_data["asks"] = sorted(order_book_data["asks"], key=lambda x: x["price"])
        
        # Limit to 10 orders per side
        order_book_data["bids"] = order_book_data["bids"][:10]
        order_book_data["asks"] = order_book_data["asks"][:10]
        
        # Update timestamp
        order_book_data["last_updated"] = datetime.now().isoformat()
        
        # Broadcast updated orderbook
        asyncio.create_task(manager.broadcast(order_book_data))
        
        return {
            "success": True,
            "tx_hash": tx_hash,
            "pair": pair,
            "price": price,
            "amount": amount,
            "type": order_type,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error processing trade: {e}")
        raise HTTPException(status_code=400, detail=f"Error processing trade: {str(e)}")

@app.get("/orderbook")
async def get_orderbook(_: bool = Depends(check_rate_limit)):
    """
    Get the current order book
    """
    return order_book_data

@app.websocket("/ws/orderbook")
async def websocket_orderbook(websocket: WebSocket):
    """
    WebSocket for real-time order book updates
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # We could process commands here if needed
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@app.get("/price_chart")
async def price_chart(
    pair: str = "MARBLE/USDT",
    timeframe: str = "1h",
    periods: int = 24,
    _: bool = Depends(check_rate_limit)
):
    """
    Generate and return a price chart for a trading pair
    """
    try:
        # Generate chart
        chart_buf = generate_price_chart(pair, timeframe, periods)
        
        # Return the chart as a streaming response
        return StreamingResponse(chart_buf, media_type="image/png")
    except Exception as e:
        logger.error(f"Error generating price chart: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating chart: {str(e)}")

# MicroOS WebUI
@app.get("/microos", response_class=HTMLResponse)
async def microos_root(request: Request):
    """
    Serve the MicroOS WebUI
    """
    vmia_status = microos.get_vmia_status()
    return templates.TemplateResponse("microos.html", {"request": request, "vmia_status": vmia_status})

# Main entry point for running the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
