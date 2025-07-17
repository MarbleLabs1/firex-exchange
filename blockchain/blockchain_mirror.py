import os
import asyncio
import json
from typing import Dict, Any, List, Optional, Callable
from loguru import logger
import aiohttp

class BlockchainMirror:
    """Mirrors blockchain state for the DEX application"""
    
    def __init__(self, rpc_url: str = None):
        self.rpc_url = rpc_url or os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
        self.solana_client = None
        self.latest_blocks = []
        self.max_blocks = 100
        self.running = False
        self.task = None
        self.subscribers = {}
    
    async def start(self) -> bool:
        """Start the blockchain mirror"""
        try:
            if self.running:
                return True
            
            self.solana_client = await self._create_client()
            if not self.solana_client:
                return False
            
            self.running = True
            self.task = asyncio.create_task(self._mirror_loop())
            
            logger.info(f"Blockchain mirror started with RPC URL: {self.rpc_url}")
            return True
        except Exception as e:
            logger.error(f"Error starting blockchain mirror: {str(e)}")
            return False
    
    async def stop(self) -> bool:
        """Stop the blockchain mirror"""
        try:
            if not self.running:
                return True
            
            self.running = False
            if self.task:
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    pass
                self.task = None
            
            logger.info("Blockchain mirror stopped")
            return True
        except Exception as e:
            logger.error(f"Error stopping blockchain mirror: {str(e)}")
            return False
    
    async def _create_client(self) -> Any:
        """Create a client to interact with the blockchain"""
        try:
            session = aiohttp.ClientSession()
            async with session.post(
                self.rpc_url,
                json={"jsonrpc": "2.0", "id": 1, "method": "getHealth"},
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if "result" in result and result["result"] == "ok":
                        logger.info("Successfully connected to Solana RPC")
                        return session
                    else:
                        logger.error(f"Blockchain health check failed: {result}")
                        await session.close()
                        return None
                else:
                    logger.error(f"Failed to connect to blockchain RPC: {response.status}")
                    await session.close()
                    return None
        except Exception as e:
            logger.error(f"Error creating blockchain client: {str(e)}")
            return None
    
    async def _mirror_loop(self):
        """Background task to mirror blockchain state"""
        while self.running:
            try:
                block_hash = await self._get_latest_block_hash()
                if block_hash:
                    block_info = await self._get_block_info(block_hash)
                    if block_info:
                        self.latest_blocks.append(block_info)
                        
                        if len(self.latest_blocks) > self.max_blocks:
                            self.latest_blocks = self.latest_blocks[-self.max_blocks:]
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in blockchain mirror loop: {str(e)}")
                await asyncio.sleep(5)
    
    async def _get_latest_block_hash(self) -> Optional[str]:
        """Get the latest block hash from the blockchain"""
        try:
            if not self.solana_client:
                return None
            
            async with self.solana_client.post(
                self.rpc_url,
                json={"jsonrpc": "2.0", "id": 1, "method": "getLatestBlockhash"},
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if "result" in result and "value" in result["result"]:
                        return result["result"]["value"]["blockhash"]
                    else:
                        logger.error(f"Invalid response for latest block hash: {result}")
                        return None
                else:
                    logger.error(f"Failed to get latest block hash: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error getting latest block hash: {str(e)}")
            return None
    
    async def _get_block_info(self, block_hash: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific block"""
        try:
            if not self.solana_client:
                return None
            
            async with self.solana_client.post(
                self.rpc_url,
                json={"jsonrpc": "2.0", "id": 1, "method": "getBlock", "params": [block_hash, {"encoding": "json", "maxSupportedTransactionVersion": 0}]},
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if "result" in result:
                        return result["result"]
                    else:
                        logger.error(f"Invalid response for block info: {result}")
                        return None
                else:
                    logger.error(f"Failed to get block info: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error getting block info: {str(e)}")
            return None
    
    def subscribe(self, account_id: str, callback: Callable):
        """Subscribe to updates for a specific account"""
        if account_id not in self.subscribers:
            self.subscribers[account_id] = []
        self.subscribers[account_id].append(callback)
    
    async def get_token_balance(self, token_account: str) -> float:
        """Get token balance for a given token account"""
        try:
            if not self.solana_client:
                return 0.0
                
            async with self.solana_client.post(
                self.rpc_url,
                json={"jsonrpc": "2.0", "id": 1, "method": "getTokenAccountBalance", "params": [token_account]},
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if "result" in result and "value" in result["result"]:
                        return float(result["result"]["value"]["uiAmount"])
                    else:
                        logger.error(f"Invalid response for token balance: {result}")
                        return 0.0
                else:
                    logger.error(f"Failed to get token balance: {response.status}")
                    return 0.0
        except Exception as e:
            logger.error(f"Error getting token balance: {str(e)}")
            return 0.0
