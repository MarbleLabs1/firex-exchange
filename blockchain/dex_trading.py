import os
import json
import time
import uuid
import asyncio
from typing import Dict, Any, List, Optional
from decimal import Decimal
from loguru import logger
import aiohttp

class DexTrading:
    """DEX trading functionality"""
    
    def __init__(self, solana_client):
        self.solana_client = solana_client
        self.orders = {}
        self.pools = {}
        self.trades = []
        self.max_trades = 100
    
    async def initialize_pools(self) -> bool:
        """Initialize DEX pools"""
        try:
            # In a real app, this would fetch pools from blockchain
            # For demo purposes, create some sample pools
            self.pools = {
                "SOL/USDC": {
                    "id": "SOL/USDC",
                    "base_token": "SOL",
                    "quote_token": "USDC",
                    "base_token_account": "58yd5dz7n1KPEBzWPY6Qf8ieXTxzZAuXDuZunNvEQ4v5",
                    "quote_token_account": "EXgMn4bm1rDBhxxNXq2pRCDERFLxupBPXPaZFGCqppZr",
                    "fee_rate": 0.003,
                    "min_size": 0.1,
                    "price_tick": 0.01,
                    "size_tick": 0.01,
                    "current_price": 75.45
                },
                "ETH/USDC": {
                    "id": "ETH/USDC",
                    "base_token": "ETH",
                    "quote_token": "USDC",
                    "base_token_account": "7Dj2oU9zFb7CwPZ6WhLC5x5cCbLcZJVoZt8XNzUXaDe3",
                    "quote_token_account": "B5g9dwq6fZh9z5S39xnx3NwSABDvM7L8ZwQwBUXygdXr",
                    "fee_rate": 0.003,
                    "min_size": 0.01,
                    "price_tick": 0.1,
                    "size_tick": 0.001,
                    "current_price": 2180.75
                },
                "BTC/USDC": {
                    "id": "BTC/USDC",
                    "base_token": "BTC",
                    "quote_token": "USDC",
                    "base_token_account": "4uQeVj5tqViQh7yWWGStvkEG1Zmhx6uasJtWCJziofM",
                    "quote_token_account": "QqCCvshxtqMAL2CVALqiJB7uEeE5mjSPsseQdDzsRUo",
                    "fee_rate": 0.003,
                    "min_size": 0.001,
                    "price_tick": 1,
                    "size_tick": 0.0001,
                    "current_price": 31450.50
                }
            }
            logger.info(f"Initialized {len(self.pools)} DEX pools")
            return True
        except Exception as e:
            logger.error(f"Error initializing DEX pools: {str(e)}")
            return False
    
    async def get_pools(self) -> Dict[str, Any]:
        """Get available pools"""
        return self.pools
    
    async def get_order_book(self, pool_id: str) -> Dict[str, Any]:
        """Get order book for a specific pool"""
        try:
            if pool_id not in self.pools:
                logger.error(f"Pool {pool_id} not found")
                return {"buy_orders": [], "sell_orders": []}
            
            # In a real app, this would fetch from blockchain
            # For demo purposes, generate sample order book
            current_price = self.pools[pool_id]["current_price"]
            
            # Generate buy orders (bids) below current price
            buy_orders = []
            for i in range(1, 11):
                price = current_price * (1 - (i * 0.005))
                size = 10 / price * (1 + i * 0.2)
                buy_orders.append({
                    "price": price,
                    "amount": size,
                    "total": price * size
                })
            
            # Generate sell orders (asks) above current price
            sell_orders = []
            for i in range(1, 11):
                price = current_price * (1 + (i * 0.005))
                size = 10 / price * (1 + i * 0.1)
                sell_orders.append({
                    "price": price,
                    "amount": size,
                    "total": price * size
                })
            
            return {
                "buy_orders": buy_orders,
                "sell_orders": sell_orders,
                "spread": sell_orders[0]["price"] - buy_orders[0]["price"],
                "spread_percentage": (sell_orders[0]["price"] - buy_orders[0]["price"]) / current_price * 100
            }
        except Exception as e:
            logger.error(f"Error getting order book: {str(e)}")
            return {"buy_orders": [], "sell_orders": []}
    
    async def create_order(self, pool_id: str, side: str, amount: Decimal, price: Decimal, 
                          slippage: Decimal, metadata: Dict[str, Any] = None) -> Optional[str]:
        """Create a new order"""
        try:
            if pool_id not in self.pools:
                logger.error(f"Pool {pool_id} not found")
                return None
            
            # Validate order parameters
            pool = self.pools[pool_id]
            if amount < Decimal(str(pool["min_size"])):
                logger.error(f"Order amount {amount} is below minimum size {pool['min_size']}")
                return None
            
            # In a real app, this would submit to blockchain
            # For demo purposes, create a simulated order
            order_id = str(uuid.uuid4())
            
            order = {
                "id": order_id,
                "pool_id": pool_id,
                "side": side,
                "amount": float(amount),
                "price": float(price),
                "slippage": float(slippage),
                "status": "open",
                "filled": 0.0,
                "created_at": time.time(),
                "updated_at": time.time(),
                "metadata": metadata or {}
            }
            
            self.orders[order_id] = order
            
            # Simulate immediate fill for market orders or crossing the spread
            if (side == "buy" and price >= pool["current_price"]) or \
               (side == "sell" and price <= pool["current_price"]):
                await self._simulate_fill(order_id)
            
            logger.info(f"Created order {order_id} for {amount} {pool['base_token']} at {price} {pool['quote_token']}")
            return order_id
        except Exception as e:
            logger.error(f"Error creating order: {str(e)}")
            return None
    
    async def _simulate_fill(self, order_id: str):
        """Simulate order fill"""
        try:
            if order_id not in self.orders:
                return
            
            order = self.orders[order_id]
            pool = self.pools[order["pool_id"]]
            
            # Simulate partial or complete fill
            fill_percentage = min(1.0, 0.8 + (0.4 * (0.5 - abs(0.5 - (order["price"] / pool["current_price"])))))
            filled_amount = order["amount"] * fill_percentage
            
            # Update order
            order["filled"] = filled_amount
            order["status"] = "filled" if fill_percentage >= 0.999 else "partially_filled"
            order["updated_at"] = time.time()
            
            # Record trade
            trade = {
                "id": str(uuid.uuid4()),
                "order_id": order_id,
                "pool_id": order["pool_id"],
                "side": order["side"],
                "price": order["price"],
                "amount": filled_amount,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "fee": filled_amount * order["price"] * pool["fee_rate"]
            }
            
            self.trades.append(trade)
            if len(self.trades) > self.max_trades:
                self.trades = self.trades[-self.max_trades:]
            
            logger.info(f"Filled order {order_id} for {filled_amount} {pool['base_token']} at {order['price']} {pool['quote_token']}")
        except Exception as e:
            logger.error(f"Error simulating fill: {str(e)}")
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""
        try:
            if order_id not in self.orders:
                logger.error(f"Order {order_id} not found")
                return False
            
            order = self.orders[order_id]
            if order["status"] in ("filled", "cancelled"):
                logger.error(f"Order {order_id} already {order['status']}")
                return False
            
            # In a real app, this would submit to blockchain
            # For demo purposes, just update the local state
            order["status"] = "cancelled"
            order["updated_at"] = time.time()
            
            logger.info(f"Cancelled order {order_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order: {str(e)}")
            return False
    
    async def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order details"""
        try:
            if order_id not in self.orders:
                logger.error(f"Order {order_id} not found")
                return None
            
            return self.orders[order_id]
        except Exception as e:
            logger.error(f"Error getting order: {str(e)}")
            return None
    
    async def get_orders(self, pool_id: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get orders filtered by pool and/or status"""
        try:
            filtered_orders = []
            
            for order in self.orders.values():
                if pool_id and order["pool_id"] != pool_id:
                    continue
                if status and order["status"] != status:
                    continue
                filtered_orders.append(order)
            
            return filtered_orders
        except Exception as e:
            logger.error(f"Error getting orders: {str(e)}")
            return []
    
    async def get_trades(self, pool_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent trades"""
        try:
            filtered_trades = []
            
            for trade in reversed(self.trades):
                if pool_id and trade["pool_id"] != pool_id:
                    continue
                filtered_trades.append(trade)
                if len(filtered_trades) >= limit:
                    break
            
            return filtered_trades
        except Exception as e:
            logger.error(f"Error getting trades: {str(e)}")
            return []

from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solana.transaction import Transaction
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solders.pubkey import Pubkey
from solders.instruction import Instruction
from solders.system_program import transfer, TransferParams
from solders.sysvar import SYSVAR_RENT_PUBKEY
import base58
import json
from typing import Dict, List, Optional, Tuple
from loguru import logger
from .solana_client import SolanaClient
from config.solana_config import (
    DEX_PROGRAM_ID,
    TOKEN_PROGRAM_ID,
    SYSTEM_PROGRAM_ID,
    MAX_RETRIES
)

class DexTrading:
    def __init__(self, solana_client: SolanaClient):
        self.client = solana_client
        self.pools: Dict[str, Dict] = {}
        self.orders: Dict[str, Dict] = {}

    async def create_pool(
        self,
        token_a: str,
        token_b: str,
        initial_liquidity_a: float,
        initial_liquidity_b: float,
        fee_rate: float = 0.003  # 0.3% default fee
    ) -> str:
        """Create a new liquidity pool for token pair"""
        try:
            # Create pool account
            pool_keypair = Keypair()
            
            # Calculate pool parameters
            pool_params = {
                "token_a": token_a,
                "token_b": token_b,
                "fee_rate": fee_rate,
                "liquidity_a": initial_liquidity_a,
                "liquidity_b": initial_liquidity_b
            }

            # Create pool instruction
            create_pool_ix = Instruction(
                program_id=Pubkey.from_string(DEX_PROGRAM_ID),
                accounts=[
                    {"pubkey": pool_keypair.pubkey, "is_signer": True, "is_writable": True},
                    {"pubkey": Pubkey.from_string(token_a), "is_signer": False, "is_writable": True},
                    {"pubkey": Pubkey.from_string(token_b), "is_signer": False, "is_writable": True},
                    {"pubkey": SYSVAR_RENT_PUBKEY, "is_signer": False, "is_writable": False}
                ],
                data=json.dumps({
                    "instruction": "create_pool",
                    "params": pool_params
                }).encode()
            )

            # Build and send transaction
            transaction = Transaction()
            transaction.add(create_pool_ix)
            
            # Sign and send transaction
            result = await self.client.client.send_transaction(
                transaction,
                pool_keypair,
                opts={"skip_confirmation": False}
            )

            pool_id = str(pool_keypair.pubkey)
            self.pools[pool_id] = pool_params
            return pool_id

        except Exception as e:
            logger.error(f"Error creating pool: {str(e)}")
            return None

    async def add_liquidity(
        self,
        pool_id: str,
        amount_a: float,
        amount_b: float
    ) -> bool:
        """Add liquidity to an existing pool"""
        try:
            pool = self.pools.get(pool_id)
            if not pool:
                raise ValueError(f"Pool {pool_id} not found")

            # Create add liquidity instruction
            add_liquidity_ix = Instruction(
                program_id=Pubkey.from_string(DEX_PROGRAM_ID),
                accounts=[
                    {"pubkey": Pubkey.from_string(pool_id), "is_signer": False, "is_writable": True},
                    {"pubkey": Pubkey.from_string(pool["token_a"]), "is_signer": False, "is_writable": True},
                    {"pubkey": Pubkey.from_string(pool["token_b"]), "is_signer": False, "is_writable": True}
                ],
                data=json.dumps({
                    "instruction": "add_liquidity",
                    "amount_a": amount_a,
                    "amount_b": amount_b
                }).encode()
            )

            # Build and send transaction
            transaction = Transaction()
            transaction.add(add_liquidity_ix)
            
            result = await self.client.client.send_transaction(
                transaction,
                opts={"skip_confirmation": False}
            )

            # Update pool state
            pool["liquidity_a"] += amount_a
            pool["liquidity_b"] += amount_b
            return True

        except Exception as e:
            logger.error(f"Error adding liquidity: {str(e)}")
            return False

    async def create_order(
        self,
        pool_id: str,
        side: str,  # "buy" or "sell"
        amount: float,
        price: float,
        slippage: float = 0.01  # 1% default slippage
    ) -> str:
        """Create a new order in the pool"""
        try:
            pool = self.pools.get(pool_id)
            if not pool:
                raise ValueError(f"Pool {pool_id} not found")

            # Generate order ID
            order_id = base58.b58encode(os.urandom(32)).decode()

            # Create order instruction
            create_order_ix = Instruction(
                program_id=Pubkey.from_string(DEX_PROGRAM_ID),
                accounts=[
                    {"pubkey": Pubkey.from_string(pool_id), "is_signer": False, "is_writable": True},
                    {"pubkey": Pubkey.from_string(pool["token_a"]), "is_signer": False, "is_writable": True},
                    {"pubkey": Pubkey.from_string(pool["token_b"]), "is_signer": False, "is_writable": True}
                ],
                data=json.dumps({
                    "instruction": "create_order",
                    "order_id": order_id,
                    "side": side,
                    "amount": amount,
                    "price": price,
                    "slippage": slippage
                }).encode()
            )

            # Build and send transaction
            transaction = Transaction()
            transaction.add(create_order_ix)
            
            result = await self.client.client.send_transaction(
                transaction,
                opts={"skip_confirmation": False}
            )

            # Store order
            self.orders[order_id] = {
                "pool_id": pool_id,
                "side": side,
                "amount": amount,
                "price": price,
                "slippage": slippage,
                "status": "open"
            }

            return order_id

        except Exception as e:
            logger.error(f"Error creating order: {str(e)}")
            return None

    async def execute_order(self, order_id: str) -> bool:
        """Execute an existing order"""
        try:
            order = self.orders.get(order_id)
            if not order:
                raise ValueError(f"Order {order_id} not found")

            pool = self.pools.get(order["pool_id"])
            if not pool:
                raise ValueError(f"Pool {order['pool_id']} not found")

            # Create execute order instruction
            execute_order_ix = Instruction(
                program_id=Pubkey.from_string(DEX_PROGRAM_ID),
                accounts=[
                    {"pubkey": Pubkey.from_string(order["pool_id"]), "is_signer": False, "is_writable": True},
                    {"pubkey": Pubkey.from_string(pool["token_a"]), "is_signer": False, "is_writable": True},
                    {"pubkey": Pubkey.from_string(pool["token_b"]), "is_signer": False, "is_writable": True}
                ],
                data=json.dumps({
                    "instruction": "execute_order",
                    "order_id": order_id
                }).encode()
            )

            # Build and send transaction
            transaction = Transaction()
            transaction.add(execute_order_ix)
            
            result = await self.client.client.send_transaction(
                transaction,
                opts={"skip_confirmation": False}
            )

            # Update order status
            order["status"] = "executed"
            return True

        except Exception as e:
            logger.error(f"Error executing order: {str(e)}")
            return False

    async def get_pool_state(self, pool_id: str) -> Dict:
        """Get current state of a pool"""
        try:
            pool = self.pools.get(pool_id)
            if not pool:
                raise ValueError(f"Pool {pool_id} not found")

            # Get pool account info
            pool_info = await self.client.get_account_info(pool_id)
            if not pool_info:
                raise ValueError(f"Pool account {pool_id} not found")

            return {
                "pool_id": pool_id,
                "token_a": pool["token_a"],
                "token_b": pool["token_b"],
                "liquidity_a": pool["liquidity_a"],
                "liquidity_b": pool["liquidity_b"],
                "fee_rate": pool["fee_rate"],
                "current_price": pool["liquidity_b"] / pool["liquidity_a"] if pool["liquidity_a"] > 0 else 0
            }

        except Exception as e:
            logger.error(f"Error getting pool state: {str(e)}")
            return None

    async def get_order_book(self, pool_id: str) -> Dict:
        """Get order book for a pool"""
        try:
            pool = self.pools.get(pool_id)
            if not pool:
                raise ValueError(f"Pool {pool_id} not found")

            # Filter orders for this pool
            pool_orders = {
                order_id: order for order_id, order in self.orders.items()
                if order["pool_id"] == pool_id and order["status"] == "open"
            }

            # Separate buy and sell orders
            buy_orders = sorted(
                [order for order in pool_orders.values() if order["side"] == "buy"],
                key=lambda x: x["price"],
                reverse=True
            )
            sell_orders = sorted(
                [order for order in pool_orders.values() if order["side"] == "sell"],
                key=lambda x: x["price"]
            )

            return {
                "pool_id": pool_id,
                "buy_orders": buy_orders,
                "sell_orders": sell_orders
            }

        except Exception as e:
            logger.error(f"Error getting order book: {str(e)}")
            return None 