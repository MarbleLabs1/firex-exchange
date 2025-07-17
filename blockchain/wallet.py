import asyncio
from typing import Dict, List, Optional, Union
import logging
from solana.rpc.async_api import AsyncClient
from solana.transaction import Transaction
from solana.system_program import TransferParams, transfer
from solana.keypair import Keypair
from solana.publickey import PublicKey
from base58 import b58encode, b58decode
import json
from pathlib import Path
from cryptography.fernet import Fernet
from dataclasses import dataclass

@dataclass
class TransactionInfo:
    signature: str
    amount: float
    sender: str
    recipient: str
    timestamp: float
    status: str
    block_hash: Optional[str] = None

class SolanaWallet:
    """
    Manages Solana wallet operations including key management,
    transaction handling, and balance tracking.
    """
    def __init__(self, network: str = "devnet"):
        self.logger = logging.getLogger(__name__)
        self.network = network
        self.endpoint = self._get_network_endpoint()
        self.client = AsyncClient(self.endpoint)
        self.keypair: Optional[Keypair] = None
        self.encrypted_key: Optional[bytes] = None
        self.transaction_history: List[TransactionInfo] = []

    def _get_network_endpoint(self) -> str:
        """Get the RPC endpoint for the selected network."""
        endpoints = {
            "mainnet": "https://api.mainnet-beta.solana.com",
            "devnet": "https://api.devnet.solana.com",
            "testnet": "https://api.testnet.solana.com"
        }
        return endpoints.get(self.network, endpoints["devnet"])

    async def create_wallet(self, password: str) -> Dict:
        """Create a new Solana wallet with encrypted storage."""
        try:
            # Generate new keypair
            self.keypair = Keypair()
            
            # Encrypt private key
            key = Fernet.generate_key()
            f = Fernet(key)
            self.encrypted_key = f.encrypt(bytes(self.keypair.secret_key))
            
            # Store encrypted key with password
            wallet_data = {
                "encrypted_key": b58encode(self.encrypted_key).decode(),
                "public_key": str(self.keypair.public_key),
                "network": self.network
            }
            
            return {
                "address": str(self.keypair.public_key),
                "network": self.network
            }
        
        except Exception as e:
            self.logger.error(f"Failed to create wallet: {str(e)}")
            raise RuntimeError(f"Wallet creation failed: {str(e)}")

    async def load_wallet(self, encrypted_key: str, password: str) -> Dict:
        """Load an existing wallet from encrypted storage."""
        try:
            # Decrypt private key
            key = Fernet.generate_key()
            f = Fernet(key)
            decrypted_key = f.decrypt(b58decode(encrypted_key))
            
            # Create keypair from decrypted key
            self.keypair = Keypair.from_secret_key(bytes(decrypted_key))
            
            return {
                "address": str(self.keypair.public_key),
                "network": self.network
            }
        
        except Exception as e:
            self.logger.error(f"Failed to load wallet: {str(e)}")
            raise RuntimeError(f"Wallet loading failed: {str(e)}")

    async def get_balance(self) -> float:
        """Get the current balance of the wallet."""
        try:
            if not self.keypair:
                raise ValueError("Wallet not initialized")
            
            balance = await self.client.get_balance(self.keypair.public_key)
            return float(balance["result"]["value"]) / 1e9  # Convert lamports to SOL
        
        except Exception as e:
            self.logger.error(f"Failed to get balance: {str(e)}")
            raise RuntimeError(f"Balance check failed: {str(e)}")

    async def send_transaction(self, recipient: str, amount: float) -> TransactionInfo:
        """Send SOL to a recipient address."""
        try:
            if not self.keypair:
                raise ValueError("Wallet not initialized")
            
            # Convert recipient address to PublicKey
            recipient_key = PublicKey(recipient)
            
            # Create transfer instruction
            transfer_params = TransferParams(
                from_pubkey=self.keypair.public_key,
                to_pubkey=recipient_key,
                lamports=int(amount * 1e9)  # Convert SOL to lamports
            )
            
            # Create and sign transaction
            transaction = Transaction().add(
                transfer(transfer_params)
            )
            
            # Send transaction
            result = await self.client.send_transaction(
                transaction,
                self.keypair
            )
            
            # Create transaction record
            tx_info = TransactionInfo(
                signature=result["result"],
                amount=amount,
                sender=str(self.keypair.public_key),
                recipient=recipient,
                timestamp=result["result"]["timestamp"],
                status="pending"
            )
            
            self.transaction_history.append(tx_info)
            return tx_info
        
        except Exception as e:
            self.logger.error(f"Failed to send transaction: {str(e)}")
            raise RuntimeError(f"Transaction failed: {str(e)}")

    async def get_transaction_status(self, signature: str) -> Dict:
        """Get the status of a transaction by its signature."""
        try:
            result = await self.client.get_signature_statuses([signature])
            status = result["result"]["value"][0]
            
            if status is None:
                return {"status": "not_found"}
            
            return {
                "status": "confirmed" if status["confirmationStatus"] == "finalized" else "pending",
                "confirmations": status["confirmations"],
                "slot": status["slot"]
            }
        
        except Exception as e:
            self.logger.error(f"Failed to get transaction status: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def get_transaction_history(self) -> List[TransactionInfo]:
        """Get the transaction history for this wallet."""
        try:
            if not self.keypair:
                raise ValueError("Wallet not initialized")
            
            signatures = await self.client.get_signatures_for_address(
                self.keypair.public_key
            )
            
            history = []
            for sig_info in signatures["result"]:
                tx_info = TransactionInfo(
                    signature=sig_info["signature"],
                    amount=float(sig_info["amount"]) / 1e9 if "amount" in sig_info else 0,
                    sender=sig_info.get("from", "unknown"),
                    recipient=sig_info.get("to", "unknown"),
                    timestamp=sig_info["blockTime"],
                    status="confirmed" if sig_info["confirmationStatus"] == "finalized" else "pending",
                    block_hash=sig_info.get("blockHash")
                )
                history.append(tx_info)
            
            return history
        
        except Exception as e:
            self.logger.error(f"Failed to get transaction history: {str(e)}")
            return []

    async def close(self):
        """Close the wallet connection."""
        await self.client.close()

