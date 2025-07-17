from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solders.pubkey import Pubkey
import base58
import json
import os
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional, Callable
from loguru import logger

class SolanaClient:
    """Client for interacting with Solana blockchain"""
    
    def __init__(self, rpc_url: str = None):
        self.rpc_url = rpc_url or os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
        self.client = AsyncClient(self.rpc_url, commitment=Confirmed)
        self.subscriptions = {}
    
    async def get_account_info(self, pubkey: str) -> Optional[Dict[str, Any]]:
        """Get account information for a given public key"""
        try:
            # For demo purposes, return simulated account info
            return {
                "address": pubkey,
                "balance": 1000000000,  # 1 SOL in lamports
                "executable": False,
                "owner": "11111111111111111111111111111111",
                "rentEpoch": 0
            }
        except Exception as e:
            logger.error(f"Error getting account info: {str(e)}")
            return None
    
    async def subscribe_to_account(self, pubkey: str, callback: Callable) -> int:
        """Subscribe to account changes"""
        try:
            # For demo purposes, just return a subscription ID
            subscription_id = len(self.subscriptions) + 1
            self.subscriptions[pubkey] = subscription_id
            return subscription_id
        except Exception as e:
            logger.error(f"Error subscribing to account: {str(e)}")
            return None
    
    async def unsubscribe_from_account(self, pubkey: str) -> bool:
        """Unsubscribe from account changes"""
        if pubkey in self.subscriptions:
            try:
                del self.subscriptions[pubkey]
                return True
            except Exception as e:
                logger.error(f"Error unsubscribing from account: {str(e)}")
        return False
    
    async def get_token_balance(self, token_account: str) -> float:
        """Get token balance for a given token account"""
        try:
            # For demo purposes, return simulated token balance
            return 100.0
        except Exception as e:
            logger.error(f"Error getting token balance: {str(e)}")
            return 0.0
    
    async def close(self) -> None:
        """Close the client connection"""
        await self.client.close()
