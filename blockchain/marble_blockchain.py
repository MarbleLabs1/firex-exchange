#!/usr/bin/env python3
import argparse
import asyncio
import cmd
import datetime
import hashlib
import json
import logging
import logging.config
import os
import random
import shlex
import socket
import stat
import sys
import time
import traceback
from typing import Dict, List, Optional, Tuple, Any

# Configure logging from external config file
if os.path.exists('logging.conf'):
    logging.config.fileConfig('logging.conf', disable_existing_loggers=False)
    logging.info("Logging configured from logging.conf")
else:
    # Fallback to basic configuration if file doesn't exist
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('blockchain.log'),
            logging.StreamHandler()
        ]
    )
    logging.warning("logging.conf not found, using basic config")
logger = logging.getLogger(__name__)

# ======== Crypto Utilities ========
class CryptoUtils:
    @staticmethod
    def generate_keypair():
        """Generate a simple public/private key pair for demonstration purposes."""
        # In a real implementation, use proper cryptographic libraries
        private_key = hashlib.sha256(str(random.getrandbits(256)).encode()).hexdigest()
        public_key = hashlib.sha256(private_key.encode()).hexdigest()
        return private_key, public_key
    
    @staticmethod
    def sign_transaction(tx_data: Dict, private_key: str) -> str:
        """Sign transaction data with private key."""
        tx_string = json.dumps(tx_data, sort_keys=True)
        signature = hashlib.sha256((tx_string + private_key).encode()).hexdigest()
        return signature
    
    @staticmethod
    def verify_signature(tx_data: Dict, signature: str, public_key: str) -> bool:
        """Verify transaction signature with public key."""
        tx_string = json.dumps(tx_data, sort_keys=True)
        # In a real implementation, this would use proper signature verification
        expected = hashlib.sha256((tx_string + hashlib.sha256(public_key.encode()).hexdigest()).encode()).hexdigest()
        return signature == expected

# ======== Blockchain Components ========
class Transaction:
    def __init__(self, sender: str, recipient: str, amount: float, fee: float = 0.001, token: str = "MARBLE"):
        self.sender = sender  # Sender's public key
        self.recipient = recipient  # Recipient's public key
        self.amount = amount
        self.fee = fee
        self.token = token
        self.timestamp = time.time()
        self.signature = ""
        self.tx_hash = ""
        
    def to_dict(self) -> Dict:
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "fee": self.fee,
            "token": self.token,
            "timestamp": self.timestamp
        }
    
    def calculate_hash(self) -> str:
        """Calculate transaction hash."""
        tx_string = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(tx_string.encode()).hexdigest()
    
    def sign(self, private_key: str) -> None:
        """Sign the transaction with sender's private key."""
        self.signature = CryptoUtils.sign_transaction(self.to_dict(), private_key)
        self.tx_hash = self.calculate_hash()
    
    def verify(self) -> bool:
        """Verify transaction signature."""
        return CryptoUtils.verify_signature(self.to_dict(), self.signature, self.sender)
    
    def __str__(self) -> str:
        return f"Transaction: {self.sender[:8]}... → {self.recipient[:8]}... Amount: {self.amount} {self.token}, Fee: {self.fee}"

class Block:
    def __init__(self, index: int, transactions: List[Transaction], previous_hash: str, timestamp: Optional[float] = None):
        self.index = index
        self.timestamp = timestamp or time.time()
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.calculate_hash()
        
    def calculate_hash(self) -> str:
        """Calculate block hash."""
        block_string = f"{self.index}{self.timestamp}{self.previous_hash}{self.nonce}"
        for tx in self.transactions:
            block_string += tx.tx_hash if hasattr(tx, 'tx_hash') and tx.tx_hash else ""
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def mine_block(self, difficulty: int) -> None:
        """Mine block by finding a hash with given difficulty."""
        target = "0" * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()
    
    def get_transactions_json(self) -> List[Dict]:
        return [tx.to_dict() for tx in self.transactions]
    
    def __str__(self) -> str:
        time_str = datetime.datetime.fromtimestamp(self.timestamp).strftime('%Y-%m-%d %H:%M:%S')
        return f"Block #{self.index} [Hash: {self.hash[:8]}...] - {len(self.transactions)} transactions - {time_str}"

class Wallet:
    def __init__(self, node=None, keypair: Optional[Tuple[str, str]] = None):
        self.node = node
        if keypair:
            self.private_key, self.public_key = keypair
        else:
            self.private_key, self.public_key = CryptoUtils.generate_keypair()
        
    def save_to_file(self, filename: str) -> bool:
        """Save wallet to file."""
        try:
            wallet_data = {
                "private_key": self.private_key,
                "public_key": self.public_key
            }
            with open(filename, 'w') as f:
                json.dump(wallet_data, f)
            return True
        except IOError as e:
            print(f"Error writing to file: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error saving wallet: {e}")
            return False
            
    @classmethod
    def load_from_file(cls, filename: str, node=None):
        """Load wallet from file."""
        try:
            with open(filename, 'r') as f:
                wallet_data = json.load(f)
            
            if "private_key" not in wallet_data or "public_key" not in wallet_data:
                raise ValueError("Invalid wallet file format: missing required keys")
                
            return cls(node, (wallet_data["private_key"], wallet_data["public_key"]))
        except FileNotFoundError:
            raise FileNotFoundError(f"Wallet file not found: {filename}")
        except json.JSONDecodeError:
            raise ValueError(f"Invalid wallet file format: not a valid JSON file")
        except Exception as e:
            raise Exception(f"Error loading wallet: {e}")
    
    def get_balance(self, token: str = None) -> Dict[str, float] or float:
        """Get wallet balance from the blockchain."""
        try:
            if self.node:
                return self.node.get_address_balance(self.public_key, token)
            return 0.0 if token else {}
        except Exception as e:
            print(f"Error retrieving balance: {e}")
            return 0.0 if token else {}
    
    def create_transaction(self, recipient: str, amount: float, token: str = "MARBLE", fee: float = 0.001) -> Transaction:
        """Create a new transaction."""
        tx = Transaction(self.public_key, recipient, amount, fee, token)
        tx.sign(self.private_key)
        return tx
    
    def send(self, recipient: str, amount: float, token: str = "MARBLE", fee: float = 0.001) -> bool:
        """Send tokens to recipient."""
        try:
            if not self.node:
                print("Error: No blockchain node connected to wallet")
                return False
                
            # Check if we have enough balance
            balances = self.get_balance()
            
            if isinstance(balances, dict):
                if token not in balances:
                    print(f"Error: You don't have any {token} tokens")
                    return False
                balance = balances[token]
            else:
                balance = balances
                
            if balance < amount + fee:
                print(f"Error: Insufficient {token} balance. Have {balance:.6f}, need {(amount + fee):.6f}")
                return False
            
            # Validate inputs
            if amount <= 0:
                print("Error: Amount must be greater than zero")
                return False
                
            if fee < 0:
                print("Error: Fee cannot be negative")
                return False
            
            # Create and send transaction
            tx = self.create_transaction(recipient, amount, token, fee)
            return self.node.add_transaction(tx)
        except Exception as e:
            print(f"Error sending transaction: {e}")
            return False

    def __str__(self) -> str:
        return f"Wallet: {self.public_key[:16]}..."

# ======== Blockchain Node Class ========
class Blockchain:
    def __init__(self, difficulty: int = 4):
        logger.info("Initializing Blockchain with difficulty: %d", difficulty)
        # Initialize blockchain with genesis block
        self.chain: List[Block] = []
        self.pending_transactions: List[Transaction] = []
        self.peers: List[str] = []
        self.difficulty = difficulty
        self.wallet = None
        self._balances = {
            "addr1": {"MARBLE": 1000, "SOL": 50, "ETH": 10},
            "addr2": {"MARBLE": 500, "SOL": 25, "ETH": 5},
        }
        self._validators = ["addr1", "addr2", "addr3"]
        self._node_count = 3
        self._poh_counter = 0
        self.create_genesis_block()
        self.node_address = "addr1"  # Default node address
        
    def create_genesis_block(self) -> None:
        """Create the first block in the chain."""
        genesis_block = Block(0, [], "0")
        genesis_block.hash = genesis_block.calculate_hash()
        self.chain.append(genesis_block)
        logger.info("Genesis block created")
        
    def get_latest_block(self) -> Block:
        """Get the most recent block in the chain."""
        return self.chain[-1]
    
    def add_transaction(self, transaction: Transaction) -> bool:
        """Add a transaction to pending transactions."""
        try:
            if isinstance(transaction, Transaction):
                # Validate transaction
                if hasattr(transaction, 'verify') and not transaction.verify():
                    logger.warning("Invalid transaction signature")
                    return False
                
                # Check sender has enough balance
                sender_balance = self.get_address_balance(transaction.sender, transaction.token)
                if isinstance(sender_balance, dict):
                    if transaction.token not in sender_balance:
                        sender_balance = 0
                    else:
                        sender_balance = sender_balance[transaction.token]
                
                if sender_balance < transaction.amount + transaction.fee:
                    logger.warning(f"Insufficient balance. Sender has {sender_balance}, needs {transaction.amount + transaction.fee}")
                    return False
                
                self.pending_transactions.append(transaction)
                logger.info(f"Transaction added to pending pool: {transaction.tx_hash[:8] if hasattr(transaction, 'tx_hash') else 'unknown'}")
                return True
            else:
                # For compatibility with the mock implementation
                sender, recipient, amount, token = transaction
                self._poh_counter += 1
                # Mock transaction
                tx = {
                    "sender": sender,
                    "recipient": recipient,
                    "amount": amount,
                    "token": token,
                    "poh_timestamp": self._poh_counter
                }
                self.pending_transactions.append(tx)
                logger.info(f"Mock transaction added: {sender} → {recipient}, {amount} {token}")
                return True
        except Exception as e:
            logger.error(f"Error adding transaction: {e}")
            return False
    
    def mine_pending_transactions(self, mining_reward_address: str) -> bool:
        """Mine pending transactions into a new block."""
        try:
            if not mining_reward_address:
                logger.error("Invalid mining reward address")
                return False
                
            # Create a backup of pending transactions in case of failure
            pending_tx_backup = self.pending_transactions.copy()
            
            # Create reward transaction
            reward_tx = Transaction("0", mining_reward_address, 1.0, 0)  # 1 coin reward
            reward_tx.sign("0")  # Special signature for mining rewards
            
            # Add reward transaction to pending transactions
            self.pending_transactions.append(reward_tx)
            
            # Create new block
            block = Block(
                len(self.chain),
                self.pending_transactions,
                self.get_latest_block().hash
            )
            
            logger.info(f"Mining block with {len(self.pending_transactions)} transactions...")
            start_time = time.time()
            block.mine_block(self.difficulty)
            end_time = time.time()
            
            self.chain.append(block)
            self.pending_transactions = []
            
            logger.info(f"Block mined in {end_time - start_time:.2f} seconds!")
            logger.info(f"Block hash: {block.hash}")
            return True
        except KeyboardInterrupt:
            # Restore pending transactions if interrupted
            self.pending_transactions = pending_tx_backup
            logger.warning("Mining interrupted. Pending transactions restored.")
            return False
        except Exception as e:
            # Restore pending transactions in case of error
            self.pending_transactions = pending_tx_backup
            logger.error(f"Error mining block: {e}")
            return False
    
    def get_address_balance(self, address: str, token: str = None) -> Dict[str, float] or float:
        """Calculate the balance of an address by scanning the blockchain."""
        try:
            if not address:
                logger.error("Invalid address")
                return 0.0 if token else {}
                
            # For mock implementation
            if hasattr(self, '_balances') and address in self._balances:
                if token:
                    return self._balances.get(address, {}).get(token, 0.0)
                return self._balances.get(address, {})
                
            # Real implementation - tracking balances by token
            balances = {}
            
            # Go through all blocks and their transactions
            for block in self.chain:

#!/usr/bin/env python3
"""
Marble Blockchain Core Implementation

This module implements the core functionality of the Marble Blockchain, including:
- Token management with locked coins
- Validator registry with stake limits
- AES-256 security for sensitive operations
- VMIA task execution and reward system

Author: Marble Team
"""

import asyncio
import base64
import datetime
import hashlib
import json
import logging
import os
import random
import secrets
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union


# External libraries
import psutil
import requests
import bip32utils
import mnemonic
import socket
import threading
import binascii
# Cryptography for AES-256
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, padding, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.fernet import Fernet
# No external blockchain dependencies in backend
# Local modules
import microos

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("MarbleBlockchain")

# Constants
MARBLE_VERSION = "2.0.0"
DEFAULT_PORT = 9090

# Token supply constants
TOTAL_MARBLE_SUPPLY = 1_000_000  # Total supply of MARBLE tokens
LOCKED_INITIAL_SUPPLY = 510_000  # Initially locked supply
CIRCULATING_INITIAL_SUPPLY = 490_000  # Initial circulating supply
DEFAULT_LOCK_PERIOD = 365 * 24 * 60 * 60  # 1 year in seconds

# Consensus and network constants
SLOT_DURATION = 400  # Duration of a slot in milliseconds
EPOCH_LENGTH = 432000  # Number of slots in an epoch (5 days worth of slots at 1 slot/sec)
NETWORK_ID = "marble-mainnet"
MINIMUM_STAKE_AMOUNT = 50  # Minimum stake amount required for validators
MAX_HISTORY_LENGTH = 1000000  # Maximum length of PoH history entries

# External integrations are handled in the frontend

# Security constants
MASTER_SECRET_KEY = "your-secret-key-123"  # Master key for encryption
LOCKED_COINS_ADDRESS = "your-address-123"  # Address for locked coins
MAX_NON_OWNER_STAKE_PERCENT = 49  # Maximum stake percentage for non-owner validators

# Directories
DATA_DIR = Path.home() / ".marble"
WALLET_DIR = DATA_DIR / "wallets"
CHAIN_DATA_DIR = DATA_DIR / "chaindata"
LOG_DIR = DATA_DIR / "logs"


class ValidationError(Exception):
    """Exception raised for blockchain validation errors."""
    pass


class WalletError(Exception):
    """Exception raised for wallet-related errors."""
    pass


class TokenError(Exception):
    """Exception raised for token-related errors."""
    pass


class ExternalIntegrationError(Exception):
    """Exception raised for external blockchain integration errors."""
    pass


class SecurityError(Exception):
    """Exception raised for security-related errors."""
    pass


class ValidatorError(Exception):
    """Exception raised for validator-related errors."""
    pass


class TransactionType(Enum):
    """Types of transactions in the Marble blockchain."""
    TRANSFER = 1
    STAKE = 2
    UNSTAKE = 3
    CREATE_TOKEN = 4
    LOCK = 5
    UNLOCK = 6
    MINT = 7
    BURN = 8
    EXTERNAL_BRIDGE = 9
    VMIA_REWARD = 10


@dataclass
class Transaction:
    """
    Represents a transaction on the Marble blockchain.
    
    Attributes:
        tx_id: Unique transaction identifier
        sender: Public key of the sender
        recipient: Public key of the recipient
        amount: Amount of tokens being transferred
        fee: Transaction fee
        tx_type: Type of transaction
        timestamp: Time when the transaction was created
        signature: Signature of the transaction
        nonce: Unique nonce to prevent replay attacks
        data: Additional data for the transaction
        token_id: ID of the token if not the native token
    """
    tx_id: str = ""
    sender: str = ""
    recipient: str = ""
    amount: float = 0.0
    fee: float = 0.0
    tx_type: TransactionType = TransactionType.TRANSFER
    timestamp: int = 0
    signature: str = ""
    nonce: int = 0
    data: Dict[str, Any] = field(default_factory=dict)
    token_id: str = "MARBLE"  # Default to native token
    
    def __post_init__(self):
        """Initialize tx_id and timestamp if not provided."""
        if not self.tx_id:
            self.tx_id = self._generate_tx_id()
        if not self.timestamp:
            self.timestamp = int(time.time() * 1000)  # Milliseconds
    
    def _generate_tx_id(self) -> str:
        """Generate a unique transaction ID."""
        unique_data = f"{self.sender}{self.recipient}{self.amount}{time.time()}{uuid.uuid4()}"
        return hashlib.sha256(unique_data.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary."""
        return {
            "tx_id": self.tx_id,
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "fee": self.fee,
            "tx_type": self.tx_type.value,
            "timestamp": self.timestamp,
            "signature": self.signature,
            "nonce": self.nonce,
            "data": self.data,
            "token_id": self.token_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Transaction':
        """Create transaction from dictionary."""
        # Convert tx_type from int to enum if needed
        if "tx_type" in data and isinstance(data["tx_type"], int):
            data["tx_type"] = TransactionType(data["tx_type"])
        return cls(**data)


class SecurityManager:
    """
    Manages encryption and security operations for the blockchain.
    Uses AES-256 for sensitive data protection.
    """
    def __init__(self, master_key: str = MASTER_SECRET_KEY):
        """
        Initialize the SecurityManager with the master key.
        
        Args:
            master_key: Master key for encryption (default: MASTER_SECRET_KEY)
        """
        self.master_key = master_key
        self.key_bytes = self._derive_key(master_key.encode())
        
    def _derive_key(self, key_material: bytes) -> bytes:
        """
        Derive a 32-byte key using PBKDF2.
        
        Args:
            key_material: Base key material
            
        Returns:
            32-byte key for AES-256
        """
        salt = b'marble_salt_123456'  # Fixed salt for reproducibility
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 32 bytes = 256 bits
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        return kdf.derive(key_material)
        
    def encrypt_data(self, data: Union[str, bytes]) -> str:
        """
        Encrypt data using AES-256-CBC.
        
        Args:
            data: Data to encrypt (string or bytes)
            
        Returns:
            Base64-encoded encrypted data
            
        Raises:
            SecurityError: If encryption fails
        """
        try:
            # Convert data to bytes
            if isinstance(data, str):
                data_bytes = data.encode('utf-8')
            else:
                data_bytes = data
                
            # Generate a random 16-byte IV
            iv = os.urandom(16)
            
            # Apply PKCS7 padding
            padder = padding.PKCS7(algorithms.AES.block_size).padder()
            padded_data = padder.update(data_bytes) + padder.finalize()
            
            # Create an encryptor
            cipher = Cipher(algorithms.AES(self.key_bytes), modes.CBC(iv), backend=default_backend())
            encryptor = cipher.encryptor()
            
            # Encrypt the data
            encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
            
            # Combine IV and encrypted data and encode as base64
            result = base64.b64encode(iv + encrypted_data).decode('utf-8')
            
            return result
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise SecurityError(f"Failed to encrypt data: {e}")
    
    def decrypt_data(self, encrypted_data: str) -> bytes:
        """
        Decrypt data using AES-256-CBC.
        
        Args:
            encrypted_data: Base64-encoded encrypted data
            
        Returns:
            Decrypted data as bytes
            
        Raises:
            SecurityError: If decryption fails
        """
        try:
            # Decode base64
            encrypted_bytes = base64.b64decode(encrypted_data)
            
            # Extract IV (first 16 bytes) and ciphertext
            iv = encrypted_bytes[:16]
            ciphertext = encrypted_bytes[16:]
            
            # Create a decryptor
            cipher = Cipher(algorithms.AES(self.key_bytes), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            
            # Decrypt the data
            padded_data = decryptor.update(ciphertext) + decryptor.finalize()
            
            # Remove padding
            unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
            data = unpadder.update(padded_data) + unpadder.finalize()
            
            return data
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise SecurityError(f"Failed to decrypt data: {e}")
    
    def secure_hash(self, data: Union[str, bytes]) -> str:
        """
        Create a secure hash of data using SHA-256.
        
        Args:
            data: Data to hash
            
        Returns:
            Hex-encoded hash
        """
        if isinstance(data, str):
            data_bytes = data.encode('utf-8')
        else:
            data_bytes = data
            
        return hashlib.sha256(data_bytes).hexdigest()
    
    def verify_admin_action(self, action_data: Dict[str, Any], signature: str) -> bool:
        """
        Verify an administrative action using a signature.
        
        Args:
            action_data: Data describing the action
            signature: Signature to verify
            
        Returns:
            True if signature is valid, False otherwise
        """
        # In a real implementation, this would use asymmetric cryptography
        # This is a simplified version for demonstration purposes
        expected_signature = self.secure_hash(json.dumps(action_data) + self.master_key)
        return signature == expected_signature


class ValidatorRegistry:
    """
    Manages validator registration, staking, and selection with a 49% stake limit
    for non-owner validators.
    """
    def __init__(self, owner_address: str = LOCKED_COINS_ADDRESS):
        """
        Initialize the validator registry.
        
        Args:
            owner_address: Address of the owner, exempt from stake limits
        """
        self.validators = {}  # address -> stake amount
        self.validator_info = {}  # address -> additional validator info
        self.total_stake = 0.0
        self.owner_address = owner_address
        self.lock = asyncio.Lock()
    
    async def add_validator(self, address: str, stake_amount: float, is_owner: bool = False) -> bool:
        """
        Add a new validator or update an existing one's stake.
        Enforces the 49% stake limit for non-owner validators.
        
        Args:
            address: Validator address
            stake_amount: Amount to stake
            is_owner: Whether this validator is the owner (exempt from stake limit)
            
        Returns:
            True if successful, False otherwise
        """
        async with self.lock:
            # Calculate what the total stake would be after this addition
            current_stake = self.validators.get(address, 0.0)
            new_total_stake = self.total_stake - current_stake + stake_amount
            
            # Check if this would exceed the non-owner stake limit (49%)
            if not is_owner and address != self.owner_address:
                stake_percentage = (stake_amount / new_total_stake) * 100
                if stake_percentage > MAX_NON_OWNER_STAKE_PERCENT:
                    logger.warning(
                        f"Validator {address} stake would exceed {MAX_NON_OWNER_STAKE_PERCENT}% "
                        f"limit: {stake_percentage:.2f}%"
                    )
                    return False
                
            # Update validator stake
            if address in self.validators:
                self.total_stake -= self.validators[address]
                
            self.validators[address] = stake_amount
            self.total_stake += stake_amount
            
            # Update validator info
            if address not in self.validator_info:
                self.validator_info[address] = {
                    "is_owner": is_owner,
                    "added_at": time.time(),
                    "tasks_completed": 0,
                    "rewards_earned": 0.0,
                    "last_active": time.time(),
                    "vmia_tasks": []
                }
            
            # Update last active time
            self.validator_info[address]["last_active"] = time.time()
            
            logger.info(f"Validator {address} added/updated with stake {stake_amount}, is_owner={is_owner}")
    async def remove_validator(self, address: str) -> bool:
        """
        Remove a validator from the registry.
        
        Args:
            address: Validator address
            
        Returns:
            True if successful, False if validator not found.
        """
        if address not in self.validators:
            return False
            
        self.total_stake -= self.validators[address]
        del self.validators[address]
        logger.info(f"Validator {address} removed")
        return True
    
    def select_slot_producer(self, slot: int, seed: bytes) -> str:
        """
        Select a validator to produce a block for the given slot.
        Uses a deterministic algorithm based on the slot number and a random seed.
        """
        if not self.validators:
            raise ValueError("No validators available to produce blocks")
            
        # Create a deterministic random selection based on slot and seed
        slot_seed = hashlib.sha256(seed + slot.to_bytes(8, byteorder='big')).digest()
        slot_seed_int = int.from_bytes(slot_seed, byteorder='big')
        
        # Select validator proportional to stake
        target = (slot_seed_int % 10000) / 10000 * self.total_stake
        cumulative = 0
        
        for address, stake in sorted(self.validators.items()):
            cumulative += stake
            if cumulative >= target:
                return address
                
        # Fallback to the validator with highest stake
        return max(self.validators.items(), key=lambda x: x[1])[0]
    
    def get_slot_time(self, slot: int) -> float:
        """Get the expected time for a given slot."""
        return slot * self.slot_duration
    
    def get_current_slot(self) -> int:
        """Get the current slot based on current time."""
        # Start time is arbitrarily chosen as the beginning of 2023
        start_time = datetime(2023, 1, 1).timestamp()
        current_time = time.time()
        
        return int((current_time - start_time) / self.slot_duration)
    
    def get_validators(self) -> Dict[str, float]:
        """Get all validators and their stakes."""
        return self.validators.copy()
    
    def get_total_stake(self) -> float:
        """Get the total stake across all validators."""
        return self.total_stake
class WalletManager:
    """
    Hierarchical Deterministic (HD) wallet manager for Marble Blockchain.
    Supports BIP32, BIP39, and BIP44 standards for wallet creation and management.
    """
    def __init__(self, storage_path: str = "wallets"):
        self.storage_path = storage_path
        self.wallets = {}  # address -> wallet object
        self.active_wallet = None
        
        # Ensure wallet directory exists
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Load existing wallets
        self._load_wallets()
        
    def _load_wallets(self):
        """Load existing wallets from storage"""
        storage_path = Path(self.storage_path)
        wallet_files = [f for f in storage_path.glob('*.json')]
        for wallet_file in wallet_files:
            try:
                with open(wallet_file, 'r') as f:
                    wallet_data = json.load(f)
                    address = wallet_data.get('address')
                    if address:
                        self.wallets[address] = wallet_data
                        logger.info(f"Loaded wallet: {address}")
            except Exception as e:
                logger.error(f"Error loading wallet {wallet_file}: {e}")
    
    def create_wallet(self, passphrase: Optional[str] = None) -> Dict:
        """
        Create a new wallet with optional passphrase.
        Returns wallet details including address and public key.
        """
        # Generate random seed or derive from passphrase
        if passphrase:
            salt = os.urandom(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            seed = kdf.derive(passphrase.encode())
        else:
            seed = os.urandom(32)
            salt = None
        
        # Generate Ed25519 key pair
        signing_key = ed25519.Ed25519PrivateKey.from_private_bytes(seed)
        verifying_key = signing_key.public_key()
        
        # Convert to hex strings
        private_key_hex = seed.hex()
        public_key_bytes = verifying_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        public_key_hex = public_key_bytes.hex()
        # Create address (0x + public key hex)
        address = f"0x{public_key_hex}"
        
        # Store wallet
        self.wallets[address] = {
            "address": address,
            "public_key": public_key_hex,
            "private_key_encrypted": self._encrypt_data(private_key_hex, passphrase or ""),
            "salt": salt.hex() if salt else None,
            "created_at": int(time.time())
        }
        
        # Save wallet to file
        wallet_file = Path(self.storage_path) / f"{address}.json"
        with open(wallet_file, "w") as f:
            json.dump(self.wallets[address], f, indent=2)
        
        return {
            "address": address,
            "public_key": public_key_hex,
            "private_key": private_key_hex,
            "salt": salt.hex() if salt else None
        }
    
    def load_wallet(self, private_key: str) -> Dict:
        """
        Load a wallet from a private key.
        Returns wallet details including address and public key.
        """
        try:
            # Convert hex to bytes
            private_key_bytes = bytes.fromhex(private_key)
            
            # Generate Ed25519 key pair
            signing_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_bytes)
            verifying_key = signing_key.public_key()
            
            # Convert to hex strings
            public_key_bytes = verifying_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            public_key_hex = public_key_bytes.hex()
            # Create address
            address = f"0x{public_key_hex}"
            
            # Store wallet
            self.wallets[address] = {
                "address": address,
                "public_key": public_key_hex,
                "private_key_encrypted": self._encrypt_data(private_key, ""),
                "created_at": int(time.time())
            }
            
            # Save wallet to file
            wallet_file = Path(self.storage_path) / f"{address}.json"
            with open(wallet_file, "w") as f:
                json.dump(self.wallets[address], f, indent=2)
            
            return {
                "address": address,
                "public_key": public_key_hex
            }
        except Exception as e:
            logger.error(f"Failed to load wallet: {e}")
            raise ValueError(f"Invalid private key: {e}")
    
    def get_balance(self, address: str, blockchain) -> Dict[str, float]:
        """
        Get the balance of tokens for an address.
        Returns a dictionary of token_id -> balance.
        """
        return blockchain.get_account_balances(address)
    
    def sign_transaction(self, tx: Transaction, address: str, passphrase: str = "") -> Transaction:
        """Sign a transaction with the wallet's private key."""
        if address not in self.wallets:
            raise ValueError(f"No wallet found for address {address}")
        
        wallet_data = self.wallets[address]
        if "private_key_encrypted" not in wallet_data:
            raise ValueError(f"Wallet for address {address} has no private key")
        
        try:
            # Decrypt private key
            private_key_hex = self._decrypt_data(wallet_data["private_key_encrypted"], passphrase)
            private_key_bytes = bytes.fromhex(private_key_hex)
            
            # Create signing key
            signing_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_bytes)
            
            # Sign transaction
            signature = signing_key.sign(tx.get_message_for_signing())
            tx.signature = base64.b64encode(signature).decode()
            
            return tx
        except Exception as e:
            logger.error(f"Failed to sign transaction: {e}")
            raise ValueError(f"Failed to sign transaction: {e}")
    
    def _encrypt_data(self, data: str, password: str) -> str:
        """Encrypt data with a password."""
        # Generate key from password
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode() or b"default"))
        
        # Encrypt
        f = Fernet(key)
        encrypted_data = f.encrypt(data.encode())
        
        # Return salt + encrypted data
        return base64.b64encode(salt + encrypted_data).decode()
    
    def _decrypt_data(self, encrypted_data: str, password: str) -> str:
        """Decrypt data with a password."""
        try:
            # Decode data
            data = base64.b64decode(encrypted_data)
            salt, encrypted = data[:16], data[16:]
            
            # Generate key from password
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode() or b"default"))
            
            # Decrypt
            f = Fernet(key)
            decrypted_data = f.decrypt(encrypted)
            
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Error decrypting data: {e}")
            raise ValueError(f"Failed to decrypt data: {e}")

class ProofOfStake:
    """
    Proof of Stake (PoS) implementation for Marble Blockchain.
    Validators are selected based on their stake amounts with
    a weighted random selection algorithm.
    """
    def __init__(self):
        self.validators = {}  # address -> stake amount
        self.total_stake = 0
        self.active_set = set()  # Currently active validators
        self.validator_performance = {}  # address -> {blocks: int, misses: int}
        self.lock = threading.Lock()
        
    def add_validator(self, address: str, stake_amount: float) -> bool:
        """Add a new validator or update stake for existing validator"""
        with self.lock:
            if stake_amount < MINIMUM_STAKE_AMOUNT:
                return False
                
            if address in self.validators:
                old_stake = self.validators[address]
                self.validators[address] += stake_amount
                self.total_stake += stake_amount
            else:
                self.validators[address] = stake_amount
                self.total_stake += stake_amount
                self.validator_performance[address] = {"blocks": 0, "misses": 0}
                
            # Auto-activate if stake is high enough
            if self.validators[address] >= MINIMUM_STAKE_AMOUNT:
                self.active_set.add(address)
                
            return True
    
    def remove_validator(self, address: str, unstake_amount: float) -> bool:
        """Remove or reduce stake for a validator"""
        with self.lock:
            if address not in self.validators:
                return False
                
            if unstake_amount >= self.validators[address]:
                # Full unstake
                unstake_amount = self.validators[address]
                self.total_stake -= unstake_amount
                del self.validators[address]
                self.active_set.discard(address)
                return True
            else:
                # Partial unstake
                self.validators[address] -= unstake_amount
                self.total_stake -= unstake_amount
                
                # Deactivate if stake falls below minimum
                if self.validators[address] < MINIMUM_STAKE_AMOUNT:
                    self.active_set.discard(address)
                    
                return True
    
    def select_validator(self) -> str:
        """Select a validator based on weighted stake probability"""
        with self.lock:
            if not self.active_set:
                return None
                
            # Filter to only active validators
            active_validators = {addr: self.validators[addr] for addr in self.active_set}
            total_active_stake = sum(active_validators.values())
            
            if total_active_stake == 0:
                return random.choice(list(self.active_set))
                
            # Weighted random selection
            selection_point = random.uniform(0, total_active_stake)
            current_sum = 0
            
            for address, stake in active_validators.items():
                current_sum += stake
                if current_sum >= selection_point:
                    return address
                    
            # Fallback in case of floating point issues
            return random.choice(list(self.active_set))
    
    def record_block_produced(self, validator_address: str):
        """Record successful block production by a validator"""
        with self.lock:
            if validator_address in self.validator_performance:
                self.validator_performance[validator_address]["blocks"] += 1
    
    def record_missed_block(self, validator_address: str):
        """Record missed block by a validator"""
        with self.lock:
            if validator_address in self.validator_performance:
                self.validator_performance[validator_address]["misses"] += 1
                
                # Penalty for missing blocks - reduce effective stake temporarily
                if self.validator_performance[validator_address]["misses"] > 5:
                    self.active_set.discard(validator_address)
                    # Can rejoin after a cooldown period
    
    def get_validator_set(self) -> Dict[str, float]:
        """Get the current set of validators and their stakes"""
        with self.lock:
            return {addr: self.validators[addr] for addr in self.active_set}
    
    def calculate_rewards(self, block_reward: float) -> Dict[str, float]:
        """Calculate rewards for validators based on their stake"""
        with self.lock:
            if not self.active_set or self.total_stake == 0:
                return {}
                
            # Filter to only active validators
            active_validators = {addr: self.validators[addr] for addr in self.active_set}
            rewards = {}
            
            for address, stake in active_validators.items():
                # Reward proportional to stake percentage
                stake_percentage = stake / self.total_stake
                rewards[address] = block_reward * stake_percentage
                
            return rewards

class ConsensusStatus(Enum):
    """Status of the consensus mechanism."""
    SYNCING = 1
    PRODUCING = 2
    VALIDATING = 3
    IDLE = 4


class NetworkMode(Enum):
    """Blockchain network modes."""
    MAINNET = 1
    TESTNET = 2
    DEVNET = 3
    LOCAL = 4



@dataclass
class Block:
    """
    Represents a block in the Marble blockchain.
    
    Attributes:
        height: Block height in the chain
        timestamp: Time when the block was created
        prev_hash: Hash of the previous block
        hash: Hash of this block
        transactions: List of transactions in the block
        validator: Public key of the validator who created the block
        signature: Signature of the validator
        poh_hash: Proof of History hash
        poh_iterations: Number of PoH iterations performed
        slot: Slot number in the epoch
        epoch: Current epoch number
        state_root: Merkle root of the state after this block
        tx_merkle_root: Merkle root of transactions
    """
    height: int
    timestamp: int
    prev_hash: str
    hash: str = ""
    transactions: List[Transaction] = field(default_factory=list)
    validator: str = ""
    signature: str = ""
    poh_hash: str = ""
    poh_iterations: int = 0
    slot: int = 0
    epoch: int = 0
    state_root: str = ""
    tx_merkle_root: str = ""
    
    def __post_init__(self):
        """Initialize hash if not provided."""
        if not self.hash:
            self.hash = self.calculate_hash()
        if not self.tx_merkle_root:
            self.tx_merkle_root = self.calculate_merkle_root()
    
    def calculate_hash(self) -> str:
        """Calculate the hash of the block."""
        tx_data = "".join([t.tx_id for t in self.transactions])
        block_data = f"{self.height}{self.timestamp}{self.prev_hash}{tx_data}{self.validator}{self.poh_hash}{self.poh_iterations}{self.slot}{self.epoch}"
        return hashlib.sha256(block_data.encode()).hexdigest()
    
    def calculate_merkle_root(self) -> str:
        """Calculate the Merkle root of the transactions."""
        if not self.transactions:
            return hashlib.sha256(b"").hexdigest()
        
        # Get transaction IDs
        tx_ids = [tx.tx_id for tx in self.transactions]
        
        # Handle odd number of transactions by duplicating the last one
        if len(tx_ids) % 2 == 1:
            tx_ids.append(tx_ids[-1])
        
        # Calculate Merkle root
        while len(tx_ids) > 1:
            next_level = []
            for i in range(0, len(tx_ids), 2):
                combined = tx_ids[i] + tx_ids[i + 1]
                next_level.append(hashlib.sha256(combined.encode()).hexdigest())
            tx_ids = next_level
            
            # If odd number at this level, duplicate the last one
            if len(tx_ids) % 2 == 1 and len(tx_ids) > 1:
                tx_ids.append(tx_ids[-1])
        
        return tx_ids[0]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert block to dictionary."""
        return {
            "height": self.height,
            "timestamp": self.timestamp,
            "prev_hash": self.prev_hash,
            "hash": self.hash,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "validator": self.validator,
            "signature": self.signature,
            "poh_hash": self.poh_hash,
            "poh_iterations": self.poh_iterations,
            "slot": self.slot,
            "epoch": self.epoch,
            "state_root": self.state_root,
            "tx_merkle_root": self.tx_merkle_root
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Block':
        """Create block from dictionary."""
        # Convert transactions from dict to Transaction objects
        if "transactions" in data:
            data["transactions"] = [Transaction.from_dict(tx) for tx in data["transactions"]]
        return cls(**data)
    
    def get_message_for_signing(self) -> bytes:
        """Get the message bytes for signing."""
        # Exclude signature and hash from the signed message
        data_to_sign = {k: v for k, v in self.to_dict().items() if k not in ["signature", "hash"]}
        # Convert transactions to dictionaries
        data_to_sign["transactions"] = [tx.to_dict() for tx in self.transactions]
        return json.dumps(data_to_sign, sort_keys=True).encode()
    
    def verify_signature(self) -> bool:
        """Verify the block signature."""
        if not self.signature:
            logger.warning(f"Block {self.height} has no signature")
            return False
            
        try:
            signature_bytes = base64.b64decode(self.signature)
            public_key_bytes = bytes.fromhex(self.validator)
            verify_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
            
            verify_key.verify(
                signature_bytes,
                self.get_message_for_signing()
            )
            return True
        except Exception as e:
            logger.error(f"Signature verification failed for block {self.height}: {e}")
            return False

class ProofOfHistory:
    """
    Implementation of Proof of History (PoH) consensus mechanism.
    
    PoH is a sequence of computation that can provide a way to cryptographically 
    verify passage of time between two events. It uses a cryptographically secure 
    function written so that output cannot be predicted from the input, and must 
    be completely executed to generate the output.
    """
    
    def __init__(self, seed: Optional[bytes] = None):
        """
        Initialize the PoH generator.
        
        Args:
            seed: Initial seed for the PoH sequence. If None, a random seed is generated.
        """
        self.history: deque = deque(maxlen=MAX_HISTORY_LENGTH)
        if seed is None:
            seed = secrets.token_bytes(32)
        self.current_hash = seed
        self.iterations = 0
        self.last_timestamp = time.time_ns() // 1_000_000  # milliseconds
        self.history.append((self.current_hash, self.iterations, self.last_timestamp))
        logger.info(f"PoH initialized with seed: {binascii.hexlify(seed).decode()}")
    
    def next_tick(self, num_iterations: int = 100000) -> Tuple[bytes, int, int]:
        """
        Advance the PoH sequence by performing hash iterations.
        
        Args:
            num_iterations: Number of hash iterations to perform.
            
        Returns:
            Tuple of (current_hash, total_iterations, timestamp)
        """
        for _ in range(num_iterations):
            self.current_hash = hashlib.sha256(self.current_hash).digest()
            self.iterations += 1
        
        # Record current time in milliseconds
        # Record current time in milliseconds
        self.last_timestamp = current_time
        
        # Store hash, iterations, and timestamp in history
        self.history.append((self.current_hash, self.iterations, current_time))
        
        return (self.current_hash, self.iterations, current_time)
    
    def verify_sequence(self, start_hash: bytes, end_hash: bytes, iterations: int) -> bool:
        """
        Verify that a PoH sequence is valid by recomputing it.
        
        Args:
            start_hash: Initial hash in the sequence
            end_hash: Expected final hash
            iterations: Number of iterations performed
            
        Returns:
            True if the sequence is valid, False otherwise
        """
        current = start_hash
        for _ in range(iterations):
            current = hashlib.sha256(current).digest()
        
        return current == end_hash
    
    def get_current_state(self) -> Tuple[bytes, int, int]:
        """Get the current state of the PoH sequence."""
        return (self.current_hash, self.iterations, self.last_timestamp)
    
    def reset(self, seed: Optional[bytes] = None) -> None:
        """Reset the PoH sequence with a new seed."""
        if seed is None:
            seed = secrets.token_bytes(32)
        self.current_hash = seed
        self.iterations = 0
        self.last_timestamp = time.time_ns() // 1_000_000
        self.history.clear()
        self.history.append((self.current_hash, self.iterations, self.last_timestamp))
        logger.info(f"PoH reset with seed: {binascii.hexlify(seed).decode()}")


class P2PNetwork:
    """
    Implementation of the peer-to-peer network for Marble Blockchain.
    
    Handles node discovery, block and transaction propagation, and consensus messages.
    Uses a gossip protocol for efficient message broadcasting and maintains connections
    with peers through persistent TCP connections.
    """
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = DEFAULT_PORT, 
                 max_peers: int = 50, node_id: Optional[str] = None,
                 standalone_mode: bool = False):
        """
        Initialize the P2P network.
        
        Args:
            host: Host address to bind to
            port: Port to listen on
            max_peers: Maximum number of peers to connect to
            node_id: Unique ID for this node, will be generated if None
            standalone_mode: If True, operate without peer connections
        """
        self.host = host
        self.port = port
        self.max_peers = max_peers
        self.node_id = node_id or str(uuid.uuid4())
        self.peers = {}  # node_id -> (host, port)
        self.active_connections = {}  # node_id -> socket
        self.message_handlers = {}  # message_type -> handler_function
        self.running = False
        self.server_socket = None
        self.server_thread = None
        self.message_queue = asyncio.Queue()
        self.message_queue = asyncio.Queue()
        self.lock = threading.RLock()
        self.standalone_mode = standalone_mode
        # Empty by default, can be configured externally
        self.bootstrap_nodes = []
        if not standalone_mode:
            # List of known seed nodes to bootstrap the network
            self.bootstrap_nodes = [
                ("seed1.marbleblockchain.io", DEFAULT_PORT),
                ("seed2.marbleblockchain.io", DEFAULT_PORT),
                ("seed3.marbleblockchain.io", DEFAULT_PORT),
            ]
        # Define message types
        self.message_types = {
            "HANDSHAKE": 0x01,
            "GET_PEERS": 0x02,
            "PEERS": 0x03,
            "GET_BLOCKS": 0x04,
            "BLOCKS": 0x05,
            "NEW_BLOCK": 0x06,
            "NEW_TX": 0x07,
            "GET_TX": 0x08,
            "TX": 0x09,
            "PING": 0x0A,
            "PONG": 0x0B,
            "CONSENSUS": 0x0C,
        }
        
        # Register message handlers
        self._register_handlers()
        
        logger.info(f"P2P network initialized with node ID: {self.node_id}")
    
    def _register_handlers(self):
        """Register handlers for different message types."""
        self.message_handlers = {
            self.message_types["HANDSHAKE"]: self._handle_handshake,
            self.message_types["GET_PEERS"]: self._handle_get_peers,
            self.message_types["PEERS"]: self._handle_peers,
            self.message_types["GET_BLOCKS"]: self._handle_get_blocks,
            self.message_types["BLOCKS"]: self._handle_blocks,
            self.message_types["NEW_BLOCK"]: self._handle_new_block,
            self.message_types["NEW_TX"]: self._handle_new_tx,
            self.message_types["GET_TX"]: self._handle_get_tx,
            self.message_types["TX"]: self._handle_tx,
            self.message_types["PING"]: self._handle_ping,
            self.message_types["PONG"]: self._handle_pong,
            self.message_types["CONSENSUS"]: self._handle_consensus,
        }
    
    async def start(self):
        """Start the P2P network server and connect to bootstrap nodes."""
        if self.running:
            return
        
        self.running = True
        
        # Start server to accept incoming connections
        self.server_thread = threading.Thread(target=self._run_server)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        # Connect to bootstrap nodes only if not in standalone mode
        if not self.standalone_mode:
            await self._connect_to_bootstrap_nodes()
        else:
            logger.info("Running in standalone mode - skipping bootstrap node connections")
        
        # Start message processor
        asyncio.create_task(self._process_message_queue())
    
    async def stop(self):
        """Stop the P2P network."""
        if not self.running:
            return
        
        self.running = False
        
        # Close all connections
        for peer_id, conn in self.active_connections.items():
            try:
                conn.close()
                logger.debug(f"Closed connection to peer {peer_id}")
            except Exception as e:
                logger.error(f"Error closing connection to peer {peer_id}: {e}")
        
        # Close server socket
        if self.server_socket:
            self.server_socket.close()
        
        # Clear data structures
        self.active_connections.clear()
        
        logger.info("P2P network stopped")
    
    def _run_server(self):
        """Run the TCP server to accept incoming connections."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)
            
            logger.info(f"P2P server listening on {self.host}:{self.port}")
            
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    client_thread = threading.Thread(target=self._handle_client, 
                                                   args=(client_socket, address))
                    client_thread.daemon = True
                    client_thread.start()
                except Exception as e:
                    if self.running:
                        logger.error(f"Error accepting connection: {e}")
        except Exception as e:
            if self.running:
                logger.error(f"Server error: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()
    
    def _handle_client(self, client_socket, address):
        """Handle incoming client connection."""
        peer_id = None
        try:
            # Send handshake
            self._send_handshake(client_socket)
            
            # Receive and process messages
            while self.running:
                data = self._receive_data(client_socket)
                if not data:
                    break
                
                message_type = data.get("type")
                payload = data.get("payload", {})
                
                # Store peer ID from handshake
                if message_type == self.message_types["HANDSHAKE"]:
                    peer_id = payload.get("node_id")
                    if peer_id:
                        with self.lock:
                            self.peers[peer_id] = (address[0], payload.get("port", address[1]))
                            self.active_connections[peer_id] = client_socket
                
                # Process message
                asyncio.run_coroutine_threadsafe(
                    self.message_queue.put((message_type, payload, peer_id)),
                    asyncio.get_event_loop()
                )
        except Exception as e:
            logger.error(f"Error handling client {address}: {e}")
        finally:
            # Clean up
            if peer_id and peer_id in self.active_connections:
                with self.lock:
                    del self.active_connections[peer_id]
            client_socket.close()
            logger.debug(f"Connection closed with {address}")
    
    async def _process_message_queue(self):
        """Process messages from the queue."""
        while self.running:
            try:
                message_type, payload, peer_id = await self.message_queue.get()
                
                # Call appropriate handler
                if message_type in self.message_handlers:
                    await self.message_handlers[message_type](payload, peer_id)
                else:
                    logger.warning(f"Received unknown message type: {message_type}")
                
                self.message_queue.task_done()
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    
    def _send_message(self, sock, message_type, payload):
        """Send a message to a peer."""
        message = {
            "type": message_type,
            "payload": payload,
            "timestamp": int(time.time() * 1000)
        }
        try:
            data = json.dumps(message).encode()
            length = len(data).to_bytes(4, byteorder='big')
            sock.sendall(length + data)
            return True
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    def _receive_data(self, sock):
        """Receive data from a socket."""
        try:
            # Receive message length (4 bytes)
            length_bytes = sock.recv(4)
            if not length_bytes:
                return None
            
            # Convert to integer
            message_length = int.from_bytes(length_bytes, byteorder='big')
            
            # Receive the actual message
            chunks = []
            bytes_received = 0
            while bytes_received < message_length:
                chunk = sock.recv(min(message_length - bytes_received, 4096))
                if not chunk:
                    raise ConnectionError("Connection closed while receiving data")
                chunks.append(chunk)
                bytes_received += len(chunk)
            
            # Combine chunks and parse JSON
            message_data = b''.join(chunks)
            return json.loads(message_data.decode())
        except Exception as e:
            logger.error(f"Error receiving data: {e}")
            return None
    
    def _send_handshake(self, sock):
        """Send handshake message to a peer."""
        payload = {
            "node_id": self.node_id,
            "version": MARBLE_VERSION,
            "port": self.port,
            "chain_id": NETWORK_ID
        }
        return self._send_message(sock, self.message_types["HANDSHAKE"], payload)
    
    async def broadcast(self, message_type, payload):
        """Broadcast a message to all connected peers."""
        success_count = 0
        with self.lock:
            peers_copy = list(self.active_connections.items())
            
        for peer_id, sock in peers_copy:
            try:
                if self._send_message(sock, message_type, payload):
                    success_count += 1
            except Exception as e:
                logger.error(f"Error broadcasting to peer {peer_id}: {e}")
                
        logger.debug(f"Broadcast message type {message_type} to {success_count} peers")
        return success_count
        
    async def connect_to_peer(self, host, port):
        """Establish connection to a new peer."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)  # 5 second timeout for connection
            sock.connect((host, port))
            
            # Send handshake
            if not self._send_handshake(sock):
                sock.close()
                return False
                
            # Start a thread to handle this connection
            client_thread = threading.Thread(target=self._handle_client, 
                                           args=(sock, (host, port)))
            client_thread.daemon = True
            client_thread.start()
            
            logger.info(f"Connected to peer {host}:{port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to peer {host}:{port}: {e}")
            return False
            
    async def _connect_to_bootstrap_nodes(self):
        """Connect to bootstrap nodes to join the network."""
        if self.standalone_mode:
            logger.info("Running in standalone mode, skipping bootstrap node connections")
            return
            
        if not self.bootstrap_nodes:
            logger.info("No bootstrap nodes configured, skipping connections")
            return
            
        connected = 0
        for host, port in self.bootstrap_nodes:
            try:
                if await self.connect_to_peer(host, port):
                    connected += 1
                    # Request peers after connecting
                    await self.get_peers_from_network()
                    if connected >= 3:  # Connect to at least 3 bootstrap nodes
                        break
            except Exception as e:
                logger.error(f"Error connecting to bootstrap node {host}:{port}: {e}")
                
        logger.info(f"Connected to {connected} bootstrap nodes")
        
    async def get_peers_from_network(self):
        """Request peers from the network."""
        with self.lock:
            peers_copy = list(self.active_connections.items())
            
        if not peers_copy:
            logger.warning("Cannot get peers: no connected peers")
            return
            
        # Select a random peer to ask for peers
        peer_id, sock = random.choice(peers_copy)
        try:
            self._send_message(sock, self.message_types["GET_PEERS"], {})
            logger.debug(f"Requested peers from {peer_id}")
        except Exception as e:
            logger.error(f"Error requesting peers: {e}")
            
    async def _handle_handshake(self, payload, peer_id):
        """Handle handshake message from peer."""
        version = payload.get("version")
        chain_id = payload.get("chain_id")
        
        if chain_id != NETWORK_ID:
            logger.warning(f"Rejected handshake from peer {peer_id} with wrong chain ID: {chain_id}")
            return
            
        logger.info(f"Completed handshake with peer {peer_id}, version {version}")
        
        # Send our peers list as a response
        if peer_id in self.active_connections:
            peers_list = [{"node_id": pid, "host": host, "port": port} 
                         for pid, (host, port) in self.peers.items() if pid != peer_id]
            try:
                self._send_message(self.active_connections[peer_id], 
                                  self.message_types["PEERS"], 
                                  {"peers": peers_list})
            except Exception as e:
                logger.error(f"Error sending peers to {peer_id}: {e}")
                
    async def _handle_get_peers(self, payload, peer_id):
        """Handle get_peers request from peer."""
        if peer_id not in self.active_connections:
            return
            
        peers_list = [{"node_id": pid, "host": host, "port": port} 
                     for pid, (host, port) in self.peers.items() if pid != peer_id]
        try:
            self._send_message(self.active_connections[peer_id], 
                              self.message_types["PEERS"], 
                              {"peers": peers_list})
            logger.debug(f"Sent {len(peers_list)} peers to {peer_id}")
        except Exception as e:
            logger.error(f"Error sending peers to {peer_id}: {e}")
            
    async def _handle_peers(self, payload, peer_id):
        """Handle peers response from peer."""
        peers_data = payload.get("peers", [])
        new_peers = 0
        
        for peer in peers_data:
            pid = peer.get("node_id")
            host = peer.get("host")
            port = peer.get("port")
            
            if pid and host and port and pid != self.node_id and pid not in self.peers:
                with self.lock:
                    self.peers[pid] = (host, port)
                new_peers += 1
                
                # Try to connect to new peers if we have less than max_peers
                if len(self.active_connections) < self.max_peers:
                    asyncio.create_task(self.connect_to_peer(host, port))
                    
        logger.debug(f"Added {new_peers} new peers from {peer_id}")
        
    async def _handle_get_blocks(self, payload, peer_id):
        """Handle get_blocks request from peer."""
        if self.blockchain is None or peer_id not in self.active_connections:
            return
            
        start_height = payload.get("start_height", 0)
        end_height = payload.get("end_height", start_height + 50)
        max_count = min(100, end_height - start_height)  # Limit to 100 blocks at a time
        
        # Get blocks from the blockchain
        blocks = self.blockchain.get_blocks_range(start_height, start_height + max_count)
        if blocks:
            blocks_data = [block.to_dict() for block in blocks]
            try:
                self._send_message(self.active_connections[peer_id], 
                                  self.message_types["BLOCKS"], 
                                  {"blocks": blocks_data})
                logger.debug(f"Sent {len(blocks)} blocks to {peer_id}")
            except Exception as e:
                logger.error(f"Error sending blocks to {peer_id}: {e}")
                
    async def _handle_blocks(self, payload, peer_id):
        """Handle blocks response from peer."""
        if self.blockchain is None:
            return
            
        blocks_data = payload.get("blocks", [])
        for block_data in blocks_data:
            try:
                block = Block.from_dict(block_data)
                asyncio.create_task(self.blockchain.receive_block(block, peer_id))
            except Exception as e:
                logger.error(f"Error processing received block: {e}")
                
        logger.debug(f"Processed {len(blocks_data)} blocks from {peer_id}")
        
    async def _handle_new_block(self, payload, peer_id):
        """Handle new_block notification from peer."""
        if self.blockchain is None:
            return
            
        try:
            block_data = payload.get("block", {})
            block = Block.from_dict(block_data)
            asyncio.create_task(self.blockchain.receive_block(block, peer_id))
            logger.debug(f"Received new block at height {block.height} from {peer_id}")
        except Exception as e:
            logger.error(f"Error processing new block from {peer_id}: {e}")
            
    async def _handle_new_tx(self, payload, peer_id):
        """Handle new_tx notification from peer."""
        if self.blockchain is None:
            return
            
        try:
            tx_data = payload.get("transaction", {})
            tx = Transaction.from_dict(tx_data)
            asyncio.create_task(self.blockchain.receive_transaction(tx, peer_id))
            logger.debug(f"Received new transaction {tx.tx_id} from {peer_id}")
        except Exception as e:
            logger.error(f"Error processing new transaction from {peer_id}: {e}")
            
    async def _handle_get_tx(self, payload, peer_id):
        """Handle get_tx request from peer."""
        if self.blockchain is None or peer_id not in self.active_connections:
            return
            
        tx_id = payload.get("tx_id")
        if not tx_id:
            return
            
        tx = self.blockchain.get_transaction(tx_id)
        if tx:
            try:
                self._send_message(self.active_connections[peer_id], 
                                  self.message_types["TX"], 
                                  {"transaction": tx.to_dict()})
                logger.debug(f"Sent transaction {tx_id} to {peer_id}")
            except Exception as e:
                logger.error(f"Error sending transaction to {peer_id}: {e}")
                
    async def _handle_tx(self, payload, peer_id):
        """Handle tx response from peer."""
        if self.blockchain is None:
            return
            
        try:
            tx_data = payload.get("transaction", {})
            tx = Transaction.from_dict(tx_data)
            asyncio.create_task(self.blockchain.receive_transaction(tx, peer_id))
        except Exception as e:
            logger.error(f"Error processing transaction response: {e}")
            
    async def _handle_ping(self, payload, peer_id):
        """Handle ping request from peer."""
        if peer_id not in self.active_connections:
            return
            
        try:
            self._send_message(self.active_connections[peer_id], 
                              self.message_types["PONG"], 
                              {"timestamp": int(time.time() * 1000)})
        except Exception as e:
            logger.error(f"Error sending pong to {peer_id}: {e}")
            
    async def _handle_pong(self, payload, peer_id):
        """Handle pong response from peer."""
        # Used for latency measurement - timestamp was sent in ping
        sent_timestamp = payload.get("timestamp", 0)
        latency = int(time.time() * 1000) - sent_timestamp
        logger.debug(f"Measured latency to {peer_id}: {latency}ms")
        
    async def _handle_consensus(self, payload, peer_id):
        """Handle consensus message from peer."""
        if self.blockchain is None:
            return
            
        message_type = payload.get("consensus_type")
        if message_type == "poh_checkpoint":
            # Handle PoH checkpoint verification
            poh_hash = payload.get("poh_hash")
            iterations = payload.get("iterations")
            timestamp = payload.get("timestamp")
            
            if poh_hash and iterations and timestamp:
                asyncio.create_task(self.blockchain.verify_poh_checkpoint(
                    poh_hash, iterations, timestamp, peer_id))
        else:
            logger.warning(f"Received unknown consensus message type: {message_type}")
            
    async def broadcast_new_block(self, block):
        """Broadcast a new block to all peers."""
        await self.broadcast(
            self.message_types["NEW_BLOCK"],
            {"block": block.to_dict()}
        )
        
    async def broadcast_new_transaction(self, tx):
        """Broadcast a new transaction to all peers.
        
        Args:
            tx: The Transaction object to broadcast
            
        Returns:
            Number of peers the transaction was successfully broadcast to
        """
        return await self.broadcast(
            self.message_types["NEW_TX"],
            {"transaction": tx.to_dict()}
        )
        
    async def request_blocks(self, start_height, end_height=None):
        """Request blocks from the network.
        
        Args:
            start_height: Starting block height
            end_height: Ending block height (optional)
        """
        if not end_height:
            end_height = start_height + 50
            
        payload = {
            "start_height": start_height,
            "end_height": end_height
        }
        
        with self.lock:
            peers_copy = list(self.active_connections.items())
            
        if not peers_copy:
            logger.warning("Cannot request blocks: no connected peers")
            if self.standalone_mode:
                logger.info("Running in standalone mode, continuing with local blocks only")
                return True
            return False
            
        try:
            # Select a random peer to request blocks from
            peer_id, sock = random.choice(peers_copy)
            self._send_message(sock, self.message_types["GET_BLOCKS"], payload)
            logger.debug(f"Requested blocks {start_height}-{end_height} from {peer_id}")
            return True
        except Exception as e:
            logger.error(f"Error requesting blocks: {e}")
            return False


class AIConsensus:
    """AI-powered consensus mechanism that enhances the hybrid PoH+PoS system."""
    
    def __init__(self):
        self.validators = {}  # address -> {stake, compute, ia_score}
        self.total_stake = 0
        self.mock_model = None
        self.last_training = 0
        self.prediction_cache = {}
        
    def calculate_ia_score(self, validator_address: str) -> float:
        """Calculate Intelligence Augmentation score for a validator."""
        if validator_address not in self.validators:
            return 0.0
            
        validator = self.validators[validator_address]
        # Combine metrics for IA score (mock implementation)
        compute_score = validator.get('compute', 0) / 100
        stake_score = validator.get('stake', 0) / 1000
        history_score = random.uniform(0.8, 1.0)  # Mock historical performance
        
        ia_score = (compute_score + stake_score + history_score) / 3
        return min(1.0, ia_score)
        
    async def train_marble_mind(self) -> Dict[str, Any]:
        """Train the AI model for price predictions and validator scoring."""
        current_time = time.time()
        if current_time - self.last_training < 3600:  # Train once per hour
            return self.prediction_cache
            
        # Mock AI model training
        predictions = {
            "price_predictions": {
                "MARBLE/USDT": random.uniform(0.95, 1.05),
                "ETH/USDT": random.uniform(0.97, 1.03)
            },
            "validator_scores": {
                addr: self.calculate_ia_score(addr)
                for addr in self.validators
            }
        }
        
        self.prediction_cache = predictions
        self.last_training = current_time
        return predictions

class SecureMinting:
    """Handles secure token minting with admin controls and reserve limits."""
    
    def __init__(self):
        self.total_supply = 0
        self.max_supply = 1_000_000  # 1M MARBLE reserve
        self.admin_addresses = set()
        self.mint_history = []
        
    def add_admin(self, address: str) -> bool:
        """Add an admin address for minting control."""
        self.admin_addresses.add(address)
        return True
        
    def mint_tokens(self, amount: int, target_address: str, admin_address: str) -> bool:
        """Mint new tokens if conditions are met."""
        if admin_address not in self.admin_addresses:
            raise ValueError("Unauthorized: Only admins can mint tokens")
            
        if self.total_supply + amount > self.max_supply:
            raise ValueError(f"Minting would exceed max supply of {self.max_supply}")
            
        self.total_supply += amount
        self.mint_history.append({
            "amount": amount,
            "target": target_address,
            "admin": admin_address,
            "timestamp": int(time.time())
        })
        return True

class RewardDistributor:
    """Handles the distribution of rewards among validators."""
    
    def __init__(self, ai_consensus: AIConsensus):
        self.ai_consensus = ai_consensus
        self.reward_history = {}
        
    def calculate_rewards(self, block_reward: float, validator_address: str) -> Dict[str, float]:
        """Calculate reward distribution based on stake, compute, and IA score."""
        if validator_address not in self.ai_consensus.validators:
            return {"stake": 0, "compute": 0, "ia_score": 0}
            
        validator = self.ai_consensus.validators[validator_address]
        ia_score = self.ai_consensus.calculate_ia_score(validator_address)
        
        # Equal distribution (33% each)
        reward_share = block_reward / 3
        rewards = {
            "stake": reward_share,
            "compute": reward_share,
            "ia_score": reward_share * ia_score  # Adjusted by IA score
        }
        
        # Record reward distribution
        if validator_address not in self.reward_history:
            self.reward_history[validator_address] = []
        self.reward_history[validator_address].append({
            "timestamp": int(time.time()),
            "rewards": rewards,
            "total": sum(rewards.values())
        })
        
        
        return rewards

# Main MarbleBlockchain class implementation
class MarbleBlockchain:
    """
    Main Marble Blockchain class that integrates all components:
    - Proof of History (PoH) for verifiable delay and time ordering
    - Proof of Stake (PoS) for validator selection
    - P2P Network for communication
    - Wallet Manager for handling keys and transactions
    
    External blockchain integration (e.g., Solana) handled in frontend via `@solana/web3.js`.
    
    The blockchain uses a hybrid PoH+PoS consensus mechanism,
    where PoH provides a verifiable delay function and timestamp for all operations,
    while PoS selects validators based on their stake.
    """
    
    def __init__(self, 
                 network_mode: NetworkMode = NetworkMode.MAINNET,
                 host: str = "0.0.0.0", 
                 port: int = DEFAULT_PORT,
                 validator_key_path: Optional[str] = None,
                 data_dir: Optional[Path] = None,
                 standalone_mode: bool = False):
        """
        Initialize the MarbleBlockchain instance.
        
        Args:
            network_mode: Network mode (MAINNET, TESTNET, DEVNET, LOCAL)
            host: Host address to bind to for P2P communication
            port: Port to listen on for P2P communication
            validator_key_path: Path to validator private key file (if this node is a validator)
            data_dir: Directory to store blockchain data
            standalone_mode: If True, operate without peer connections
        """
        self.network_mode = network_mode
        self.data_dir = data_dir or DATA_DIR
        self.standalone_mode = standalone_mode
        
        # Initialize AI consensus and related components
        self.ai_consensus = AIConsensus()
        self.secure_minting = SecureMinting()
        self.reward_distributor = RewardDistributor(self.ai_consensus)
        
        # Create blockchain state
        self.mempool = {}  # tx_id -> Transaction
        self.balances = {}  # address -> {token_id -> amount}
        self.blocks = []  # List of blocks in the chain
        self.last_block_time = 0
        self.current_slot = 0
        self.current_epoch = 0
        self.chain_head = None
        self.genesis_block_created = False
        self.consensus_status = ConsensusStatus.SYNCING
        
        # Initialize components
        self.poh = ProofOfHistory()
        self.pos = ProofOfStake()
        self.p2p = P2PNetwork(host=host, port=port, standalone_mode=standalone_mode)
        self.wallet_manager = WalletManager(str(WALLET_DIR))
        
        # Set blockchain reference in P2P network
        self.p2p.blockchain = self
        
        # Load validator key if provided
        self.validator_key = None
        self.is_validator = False
        if validator_key_path:
            self._load_validator_key(validator_key_path)
        
        # Create locks for thread safety
        self.state_lock = threading.RLock()
        self.mempool_lock = threading.RLock()
        
        # Background tasks
        self.tasks = []
        
        logger.info(f"Marble Blockchain initialized with network mode: {network_mode.name}")
    
    async def start(self):
        """Start the blockchain node."""
        # Start P2P network
        await self.p2p.start()
        
        # Create or load genesis block
        if not self.genesis_block_created:
            if not self._load_chain_state():
                self._create_genesis_block()
        
        # Start background tasks
        task1 = asyncio.create_task(self._slot_producer())
        task2 = asyncio.create_task(self._mempool_processor())
        task3 = asyncio.create_task(self._state_synchronizer())
        
        self.tasks = [task1, task2, task3]
        
        if self.is_validator:
            # If we're a validator, start the validator task
            task4 = asyncio.create_task(self._validator_task())
            self.tasks.append(task4)
            logger.info("Started node in validator mode")
        else:
            self.consensus_status = ConsensusStatus.SYNCING
            logger.info("Started node in regular mode")

        if self.standalone_mode:
            logger.info("Running in standalone mode (no peer connections required)")
            # In standalone mode, immediately transition to PRODUCING/IDLE state
            self.consensus_status = ConsensusStatus.PRODUCING if self.is_validator else ConsensusStatus.IDLE
        
        logger.info("Marble Blockchain node started successfully")
    async def stop(self):
        """Stop the blockchain node."""
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # Stop P2P network
        await self.p2p.stop()
        
        # Save chain state
        self._save_chain_state()
        
        logger.info("Marble Blockchain node stopped")
    
    def _create_genesis_block(self):
        """Create the genesis block with initial allocations."""
        with self.state_lock:
            # Create token allocations for genesis block
            allocations = {
                # Example: Initial token distribution
                "MarbleTeamWallet": 10_000_000,
                "DevelopmentFund": 5_000_000,
                "CommunityPool": 5_000_000,
                # Add more allocations as needed
            }
            
            # Create transactions for initial allocations
            transactions = []
            timestamp = int(time.time() * 1000)
            
            for recipient, amount in allocations.items():
                tx = Transaction(
                    tx_id="",  # Will be auto-generated
                    sender="GenesisWallet",
                    recipient=recipient,
                    amount=amount,
                    fee=0,  # No fee for genesis transactions
                    tx_type=TransactionType.TRANSFER,
                    timestamp=timestamp,
                    data={"genesis": True}
                )
                transactions.append(tx)
            
            # Get initial PoH hash
            poh_hash, iterations, poh_timestamp = self.poh.get_current_state()
            
            # Create genesis block
            genesis_block = Block(
                height=0,
                timestamp=timestamp,
                prev_hash="0" * 64,  # Genesis block has no previous hash
                transactions=transactions,
                poh_hash=poh_hash.hex(),
                poh_iterations=iterations,
                slot=0,
                epoch=0
            )
            
            # Update blockchain state
            self.blocks.append(genesis_block)
            self.chain_head = genesis_block
            self.genesis_block_created = True
            self.last_block_time = timestamp
            
            # Apply genesis transactions to state
            for tx in transactions:
                if tx.recipient not in self.balances:
                    self.balances[tx.recipient] = {}
                
                if tx.token_id not in self.balances[tx.recipient]:
                    self.balances[tx.recipient][tx.token_id] = 0
                
                self.balances[tx.recipient][tx.token_id] += tx.amount
            
            logger.info(f"Genesis block created with {len(transactions)} allocations")
            return genesis_block
    
    def _load_chain_state(self):
        """Load blockchain state from disk."""
        try:
            # Check if state files exist
            # Check if state files exist
            state_file = Path(self.data_dir) / "state.json"
            if not blocks_file.exists() or not state_file.exists():
                logger.info("No existing blockchain state found")
                return False
            
            # Load blocks
            with open(blocks_file, "r") as f:
                blocks_data = json.load(f)
                self.blocks = [Block.from_dict(block_data) for block_data in blocks_data]
            
            # Load state
            with open(state_file, "r") as f:
                state_data = json.load(f)
                self.balances = state_data.get("balances", {})
                self.last_block_time = state_data.get("last_block_time", 0)
                self.current_slot = state_data.get("current_slot", 0)
                self.current_epoch = state_data.get("current_epoch", 0)
            
            if self.blocks:
                self.chain_head = self.blocks[-1]
                self.genesis_block_created = True
                logger.info(f"Loaded blockchain state with {len(self.blocks)} blocks")
                return True
            else:
                logger.warning("Loaded empty blockchain state")
                return False
                
        except Exception as e:
            logger.error(f"Error loading blockchain state: {e}")
            return False
    
    def _save_chain_state(self):
        """Save blockchain state to disk."""
        try:
            # Ensure data directory exists
            self.data_dir.mkdir(exist_ok=True, parents=True)
            
            # Save blocks
            blocks_file = Path(self.data_dir) / "blocks.json"
            with open(blocks_file, "w") as f:
                blocks_data = [block.to_dict() for block in self.blocks]
                json.dump(blocks_data, f, indent=2)
            
            # Save state
            state_file = Path(self.data_dir) / "state.json"
            with open(state_file, "w") as f:
                state_data = {
                    "balances": self.balances,
                    "last_block_time": self.last_block_time,
                    "current_slot": self.current_slot,
                    "current_epoch": self.current_epoch
                }
                json.dump(state_data, f, indent=2)
            
            logger.info(f"Saved blockchain state with {len(self.blocks)} blocks")
            return True
        except Exception as e:
            logger.error(f"Error saving blockchain state: {e}")
            return False
    
    def _load_validator_key(self, key_path):
        """Load validator private key from file."""
        try:
            key_path = Path(key_path)
            with open(key_path, "rb") as f:
                key_data = f.read()
                
            private_key = ed25519.Ed25519PrivateKey.from_private_bytes(key_data)
            public_key = private_key.public_key()
            public_key_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            
            self.validator_key = private_key
            self.validator_address = public_key_bytes.hex()
            self.is_validator = True
            
            logger.info(f"Loaded validator key for address: {self.validator_address}")
            return True
        except Exception as e:
            logger.error(f"Error loading validator key: {e}")
            return False
    
    async def create_wallet(self, password: str) -> Tuple[str, str]:
        """
        Create a new wallet with a mnemonic seed phrase.
        
        Args:
            password: Password to encrypt the wallet
            
        Returns:
            Tuple of (address, mnemonic)
        """
        try:
            # Generate private key
            private_key = ed25519.Ed25519PrivateKey.generate()
            
            # Get public key
            public_key = private_key.public_key()
            public_key_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            
            # Convert to address
            address = public_key_bytes.hex()
            
            # Generate mnemonic
            m = mnemonic.Mnemonic("english")
            seed_phrase = m.generate()
            
            # Save wallet
            wallet_data = {
                "address": address,
                "seed_phrase_protected": self._encrypt_data(seed_phrase, password),
                "created_at": int(time.time())
            }
            wallet_file = Path(WALLET_DIR) / f"{address}.json"
            with open(wallet_file, "w") as f:
                json.dump(wallet_data, f, indent=2)
            
            # Initialize balance
            with self.state_lock:
                if address not in self.balances:
                    self.balances[address] = {"MARBLE": 0}
            
            logger.info(f"Created new wallet with address: {address}")
            return address, seed_phrase
            
        except Exception as e:
            logger.error(f"Error creating wallet: {e}")
            raise WalletError(f"Failed to create wallet: {e}")
    
    def _encrypt_data(self, data: str, password: str) -> str:
        """Encrypt data with a password."""
        # Generate key from password
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        
        # Encrypt
        f = Fernet(key)
        encrypted_data = f.encrypt(data.encode())
        
        # Return salt + encrypted data
        return base64.b64encode(salt + encrypted_data).decode()
    
    def _decrypt_data(self, encrypted_data: str, password: str) -> str:
        """Decrypt data with a password."""
        # Decode data
        data = base64.b64decode(encrypted_data)
        salt, encrypted = data[:16], data[16:]
        
        # Generate key from password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        
        # Decrypt
        f = Fernet(key)
        return f.decrypt(encrypted).decode()
    
    async def create_transaction(self, sender_address: str, recipient_address: str, amount: float, 
                             token_id: str = "MARBLE", tx_type: TransactionType = TransactionType.TRANSFER, 
                             fee: float = 0.001, data: Dict[str, Any] = None) -> Transaction:
        """
        Create a new transaction and broadcast it to the network.
        
        Args:
            sender_address: Address of the sender
            recipient_address: Address of the recipient
            amount: Amount to transfer
            token_id: ID of the token to transfer
            tx_type: Type of transaction
            fee: Transaction fee
            data: Additional data for the transaction
            
        Returns:
            The created Transaction object
        """
        # Increment PoH time for each transaction
        self.poh_time += 1
        current_time = int(time.time())
        time_diff = current_time - self.poh_last_block_time
        logger.info(f"PoH counter incremented to {self.poh_time} (time since last block: {time_diff}s)")
        # Validate sender address
        if not sender_address:
            raise ValueError("Sender address is required")
            
        # Validate recipient address
        if not recipient_address:
            raise ValueError("Recipient address is required")
            
        # Check sender balance
        with self.state_lock:
            if sender_address not in self.balances:
                raise ValueError(f"Sender {sender_address} has no balance")
                
            if token_id not in self.balances[sender_address]:
                raise ValueError(f"Sender has no {token_id} tokens")
                
            if self.balances[sender_address][token_id] < amount + fee:
                raise ValueError(f"Insufficient balance: {self.balances[sender_address][token_id]} < {amount + fee}")
        
        # Create transaction
        tx = Transaction(
            tx_id="",  # Will be auto-generated
            sender=sender_address,
            recipient=recipient_address,
            amount=amount,
            fee=fee,
            tx_type=tx_type,
            timestamp=int(time.time() * 1000),
            nonce=random.randint(0, 2**32 - 1),
            data=data or {},
            token_id=token_id
        )
        
        # Add to mempool
        with self.mempool_lock:
            self.mempool[tx.tx_id] = tx
            
        # Broadcast to network
        await self.p2p.broadcast_new_transaction(tx)
        
        logger.info(f"Created and broadcast transaction {tx.tx_id}")
        return tx
        
    async def process_block(self, block: Block) -> bool:
        """
        Process a new block and update blockchain state.
        
        Args:
            block: The block to process
            
        Returns:
            True if the block was successfully processed, False otherwise
        """
        # Increment PoH time for block processing
        # Increment PoH time for block processing
        self.poh_time += 1
        self.poh_last_block_time = int(time.time())
        logger.info(f"PoH counter incremented to {self.poh_time} for block processing at timestamp {self.poh_last_block_time}")
        
        # Validate block
        if not self.validate_block(block):
            logger.warning(f"Block {block.height} validation failed")
            return False
        with self.state_lock:
            # Check if block already exists
            if block.height < len(self.blocks) and self.blocks[block.height].hash == block.hash:
                logger.debug(f"Block {block.height} already exists in chain")
                return True
                
            # Check if this is the next block
            if block.height != len(self.blocks):
                logger.warning(f"Expected block at height {len(self.blocks)}, got {block.height}")
                return False
                
            # Apply transactions
            for tx in block.transactions:
                # Skip if transaction is invalid
                if not tx.verify_signature():
                    logger.warning(f"Invalid signature for transaction {tx.tx_id}")
                    continue
                    
                # Process based on transaction type
                if tx.tx_type == TransactionType.TRANSFER:
                    # Debit sender
                    if tx.sender in self.balances and tx.token_id in self.balances[tx.sender]:
                        self.balances[tx.sender][tx.token_id] -= (tx.amount + tx.fee)
                        
                    # Credit recipient
                    if tx.recipient not in self.balances:
                        self.balances[tx.recipient] = {}
                    if tx.token_id not in self.balances[tx.recipient]:
                        self.balances[tx.recipient][tx.token_id] = 0
                    self.balances[tx.recipient][tx.token_id] += tx.amount
                    
                    # Record fee to validator
                    if block.validator in self.balances:
                        if tx.token_id not in self.balances[block.validator]:
                            self.balances[block.validator][tx.token_id] = 0
                        self.balances[block.validator][tx.token_id] += tx.fee
                
                elif tx.tx_type == TransactionType.STAKE:
                    # Handle staking
                    stake_amount = tx.amount
                    self.pos.add_validator(tx.sender, stake_amount)
                    
                    # Deduct from balance
                    if tx.sender in self.balances and tx.token_id in self.balances[tx.sender]:
                        self.balances[tx.sender][tx.token_id] -= (stake_amount + tx.fee)
            
                elif tx.tx_type == TransactionType.UNSTAKE:
                    # Handle unstaking
                    unstake_amount = tx.amount
                    self.pos.remove_validator(tx.sender, unstake_amount)
                    
                    # Add back to balance
                    if tx.sender not in self.balances:
                        self.balances[tx.sender] = {}
                    if tx.token_id not in self.balances[tx.sender]:
                        self.balances[tx.sender][tx.token_id] = 0
                    self.balances[tx.sender][tx.token_id] += unstake_amount
            
                # Remove from mempool if present
                with self.mempool_lock:
                    if tx.tx_id in self.mempool:
                        del self.mempool[tx.tx_id]
            
            # Add block to chain
            self.blocks.append(block)
            self.chain_head = block
            self.last_block_time = block.timestamp
            self.current_slot = block.slot
            self.current_epoch = block.epoch
            
            # Trigger checkpoint save periodically
            if block.height % 100 == 0:
                self._save_chain_state()
                
            logger.info(f"Processed block {block.height} with {len(block.transactions)} transactions")
            return True
    
    def disconnect_node(self, node_address: str) -> bool:
        """
        Disconnect from a node in the P2P network
        
        Args:
            node_address: The address of the node to disconnect from
            
        Returns:
            True if disconnection was successful, False otherwise
        """
        if node_address in self.connected_nodes:
            self.connected_nodes.remove(node_address)
            self.node_count = len(self.connected_nodes)
            logger.info(f"Disconnected from node: {node_address}. Total connected nodes: {self.node_count}")
            return True
        return False
    
    def get_connected_nodes(self) -> List[str]:
        """Get list of all connected nodes"""
        return self.connected_nodes
    
    def check_validator_stake(self, validator_address: str) -> float:
        """
        Check the stake amount for a validator
        
        Args:
            validator_address: Address of the validator to check
            
        Returns:
            Stake amount, or 0 if validator not found
        """
        if validator_address in self.validators:
            stake = self.validators[validator_address]
            logger.info(f"Validator {validator_address} has stake of {stake}")
            return stake
        logger.warning(f"Validator {validator_address} not found")
        return 0
    
    def add_validator(self, validator_address: str, stake: float) -> bool:
        """
        Add a new validator or update stake for existing validator
        
        Args:
            validator_address: Address of the validator
            stake: Amount to stake
            
        Returns:
            True if successful, False otherwise
        """
        min_stake = 50  # Minimum required stake
        
        if stake < min_stake:
            logger.warning(f"Stake amount {stake} is below minimum requirement of {min_stake}")
            return False
            
        prev_stake = self.validators.get(validator_address, 0)
        self.validators[validator_address] = stake
        self.total_stake = sum(self.validators.values())
        
        if prev_stake > 0:
            logger.info(f"Updated stake for validator {validator_address} from {prev_stake} to {stake}")
        else:
            return True
    
    def select_validator(self) -> str:
        """
        Select a validator based on stake weight
        
        Returns:
            Address of the selected validator
        """
        # Get active validators
        active_validators = {addr: stake for addr, stake in self.validators.items() 
                            if addr in self.active_validators}
        
        if not active_validators:
            logger.warning("No active validators available")
            return None
            
        # Calculate total active stake
        active_stake = sum(active_validators.values())
        
        # Select validator proportional to stake
        target = random.uniform(0, active_stake)
        current_sum = 0
        
        for validator, stake in active_validators.items():
            current_sum += stake
            if current_sum >= target:
                logger.info(f"Selected validator {validator} with stake {stake}")
                return validator
                
        # Fallback to the validator with highest stake
        selected = max(active_validators.items(), key=lambda x: x[1])[0]
        logger.info(f"Selected validator (fallback) {selected}")
        return selected
        
    def connect_node(self, node_address: str) -> bool:
        """
        Connect to a new node in the P2P network
        
        Args:
            node_address: The address of the node to connect to
            
        Returns:
            True if connection was successful, False otherwise
        """
        if node_address not in self.connected_nodes:
            self.connected_nodes.append(node_address)
            self.node_count = len(self.connected_nodes)
            logger.info(f"Connected to node: {node_address}. Total connected nodes: {self.node_count}")
            # Mock P2P message
            logger.info(f"P2P: Sending node discovery message to {node_address}")
            logger.info(f"P2P: Received peer list from {node_address}")
            return True
        return False
    def validate_block(self, block: Block) -> bool:
        """
        Validate a block
        
        Args:
            block: The block to validate
            
        Returns:
            True if the block is valid, False otherwise
        """
        # Check if validator has enough stake
        if block.validator:
            stake = self.check_validator_stake(block.validator)
            if stake <= 0:
                logger.warning(f"Block validation failed: validator {block.validator} has no stake")
                return False
            logger.info(f"Validated block with PoH timestamp {self.poh_time}")
            
        # Increment PoH time for block validation
        self.poh_time += 10  # Validation is more "expensive" in PoH time
        logger.info(f"PoH counter incremented to {self.poh_time} for block validation")
        # Check block signature
        if not block.verify_signature():
            logger.warning(f"Invalid block signature for block {block.height}")
            return False
            
        # Check previous hash
        if block.height > 0:
            with self.state_lock:
                if block.height > len(self.blocks):
                    logger.warning(f"Block height {block.height} is ahead of current chain length {len(self.blocks)}")
                    return False
                    
                if block.height == len(self.blocks):
                    # This is the next block, check previous hash
                    if block.prev_hash != self.chain_head.hash:
                        logger.warning(f"Block {block.height} has invalid previous hash")
                        return False
        
        # Verify PoH hash if available
        if block.poh_hash and block.poh_iterations > 0:
            # We'd normally verify the PoH sequence here, but this is simplified
            # Real implementation would use the PoH to verify the hash is valid
            pass
            
        # Validate all transactions
        for tx in block.transactions:
            if not tx.verify_signature():
                logger.warning(f"Transaction {tx.tx_id} has invalid signature")
                return False
                
            # Check for sufficient balance (simplified)
            if tx.tx_type == TransactionType.TRANSFER:
                with self.state_lock:
                    if tx.sender in self.balances and tx.token_id in self.balances[tx.sender]:
                        if self.balances[tx.sender][tx.token_id] < tx.amount + tx.fee:
                            logger.warning(f"Insufficient balance for transaction {tx.tx_id}")
                            return False
        
        # Check merkle root
        calculated_merkle = block.calculate_merkle_root()
        if block.tx_merkle_root and calculated_merkle != block.tx_merkle_root:
            logger.warning(f"Block {block.height} has invalid merkle root")
            return False
            
        logger.debug(f"Block {block.height} passed validation")
        return True
        
    def get_account_balances(self, address: str) -> Dict[str, float]:
        """
        Get the account balances for a given address.
        
        Args:
            address: The address to check
            
        Returns:
            Dictionary of token_id -> balance
        """
        with self.state_lock:
            if address not in self.balances:
                return {}
            return self.balances[address].copy()
            
    async def sync_with_network(self) -> bool:
        """
        Synchronize the blockchain state with the network.
        
        Returns:
            True if sync was successful, False otherwise
        """
        # Check if we're in standalone mode
        if self.standalone_mode or (hasattr(self, 'p2p') and self.p2p and self.p2p.standalone_mode):
            logger.info("Running in standalone mode, skipping network synchronization")
            self.consensus_status = ConsensusStatus.PRODUCING if self.is_validator else ConsensusStatus.IDLE
            return True
            
        # Get our current height
        current_height = 0
        with self.state_lock:
            current_height = len(self.blocks)
            
        # Request blocks in batches
        batch_size = 50
        synced = False
        retries = 0
        
        while not synced and retries < 3:
            # Request next batch of blocks
            success = await self.p2p.request_blocks(current_height, current_height + batch_size)
            if not success:
                retries += 1
                await asyncio.sleep(1)
                continue
                
            # Wait for blocks to be processed
            await asyncio.sleep(2)
            
            # Check if we received new blocks
            with self.state_lock:
                new_height = len(self.blocks)
                if new_height > current_height:
                    current_height = new_height
                    retries = 0
                else:
                    # No new blocks received, we might be fully synced
                    synced = True
        
        if synced:
            self.consensus_status = ConsensusStatus.PRODUCING if self.is_validator else ConsensusStatus.IDLE
            logger.info(f"Blockchain synchronized to height {current_height}")
        else:
            logger.warning("Failed to synchronize blockchain with network")
            
        return synced
        
    async def _slot_producer(self):
        """
        Background task that advances slots and epochs.
        """
        while True:
            try:
                # Calculate current slot based on time
                epoch_start_time = datetime.datetime(2023, 1, 1).timestamp() * 1000  # milliseconds
                # Rest of the function implementation goes here
                current_time = time.time() * 1000  # Convert to milliseconds
                elapsed_time = current_time - epoch_start_time
                current_slot = int(elapsed_time / SLOT_DURATION)
                current_epoch = int(current_slot / EPOCH_LENGTH)
                
                # Update blockchain state
                self.current_slot = current_slot
                self.current_epoch = current_epoch
                
                # Check if we're the slot leader
                if self.is_validator:
                    slot_leader = self.select_validator()
                    if slot_leader == self.validator_address:
                        # We're the leader, produce a block
                        await self._produce_block(current_slot, current_epoch)
                
                # Wait until the next slot
                next_slot_time = epoch_start_time + (current_slot + 1) * SLOT_DURATION
                sleep_time = (next_slot_time - current_time) / 1000  # Convert back to seconds
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                else:
                    # We're behind, don't sleep
                    await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in slot producer: {e}")
                # Sleep a bit before retrying
                await asyncio.sleep(1)
                
    # CLI INTEGRATION METHODS
    
    def start_node(self, local_address="addr1") -> bool:
        """
        Start the blockchain node with mock P2P connections
        
        Args:
            local_address: Local node address
            
        Returns:
            True if node started successfully
        """
        # Simulate node startup
        logger.info(f"Node started at {local_address}")
        logger.info(f"Connected to {len(self.connected_nodes)} nodes")
        
        # Mock P2P messages
        for node in self.connected_nodes:
            logger.info(f"P2P: Established connection with {node}")
        
        # Initialize mock PoH
        self.poh_time = 0
        self.poh_last_block_time = int(time.time())
        logger.info(f"PoH initialized at time {self.poh_last_block_time}")
        
        return True
    
    def get_balance(self, address: str) -> Dict[str, float]:
        """
        Get balance for an address
        
        Args:
            address: Wallet address
            
        Returns:
            Dictionary of token balances
        """
        # Check if address exists in our mock balances
        if address in self.token_balances:
            return self.token_balances[address]
        return {}

    async def run_vmia_task(self, validator, task):
        """
        Run a VMIA (Virtual Machine Intelligence Augmentation) task for a validator.
        
        Args:
            validator: The validator address to run the task for
            task: The type of task to run
            
        Returns:
            Task completion results
        """
        try:
            # Use psutil for CPU metrics
            cpu_effort = psutil.cpu_percent(interval=1.0)
            
            # Simulate task execution
            logger.info(f"Running VMIA task '{task}' for validator {validator}")
            logger.info(f"CPU effort: {cpu_effort}%")
            
            # Calculate reward based on effort
            reward = (cpu_effort / 100.0) * 0.01  # 0.01 MARBLE per 100% CPU utilization
            
            # Record task completion
            task_data = {
                "validator": validator,
                "task": task,
                "cpu_effort": cpu_effort,
                "timestamp": int(time.time()),
                "reward": reward
            }
            
            # In a real implementation, you'd add this to a database or blockchain
            logger.info(f"VMIA task completed with reward {reward} MARBLE")
            
            return task_data
            
        except Exception as e:
            logger.error(f"Error running VMIA task: {e}")
            logger.error(f"Error running VMIA task: {e}")

    async def _mempool_processor(self):
        """
        Background task that processes transactions in the mempool.
        Validates transactions and prepares them for inclusion in blocks.
        """
        while True:
            try:
                # Get a snapshot of the current mempool
                with self.mempool_lock:
                    pending_txs = list(self.mempool.values())
                
                if pending_txs:
                    logger.info(f"Processing {len(pending_txs)} transactions in mempool")
                    
                    # Process in batches of 50
                    batch_size = 50
                    for i in range(0, len(pending_txs), batch_size):
                        batch = pending_txs[i:i+batch_size]
                        valid_txs = []
                        invalid_txs = []
                        
                        # Validate transactions
                        for tx in batch:
                            try:
                                # Check signature
                                if not hasattr(tx, 'verify_signature') or not tx.verify_signature():
                                    logger.warning(f"Invalid signature for transaction {tx.tx_id}")
                                    invalid_txs.append(tx)
                                    continue
                                
                                # Check balance
                                with self.state_lock:
                                    if tx.sender not in self.balances:
                                        logger.warning(f"Sender {tx.sender} has no balance")
                                        invalid_txs.append(tx)
                                        continue
                                        
                                    if tx.token_id not in self.balances[tx.sender]:
                                        logger.warning(f"Sender {tx.sender} has no {tx.token_id} tokens")
                                        invalid_txs.append(tx)
                                        continue
                                        
                                    if self.balances[tx.sender][tx.token_id] < tx.amount + tx.fee:
                                        logger.warning(f"Insufficient balance for tx {tx.tx_id}: {self.balances[tx.sender][tx.token_id]} < {tx.amount + tx.fee}")
                                        invalid_txs.append(tx)
                                        continue
                                
                                # Check for duplicate transactions
                                # Additional validation logic can be added here
                                
                                # If all checks pass, add to valid transactions
                                valid_txs.append(tx)
                                
                            except Exception as e:
                                logger.error(f"Error validating transaction {tx.tx_id}: {e}")
                                invalid_txs.append(tx)
                        
                        # Remove invalid transactions from mempool
                        with self.mempool_lock:
                            for tx in invalid_txs:
                                if tx.tx_id in self.mempool:
                                    del self.mempool[tx.tx_id]
                                    
                        logger.info(f"Processed batch of {len(batch)} transactions: {len(valid_txs)} valid, {len(invalid_txs)} invalid")
                        
                        # Short sleep between batches to prevent CPU hogging
                        await asyncio.sleep(0.1)
                
                # Sleep before checking mempool again
                await asyncio.sleep(1.0)
                
            except asyncio.CancelledError:
                logger.info("Mempool processor task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in mempool processor: {e}")
                await asyncio.sleep(5.0)  # Longer sleep on error

    async def _state_synchronizer(self):
        """
        Background task that synchronizes the blockchain state with the network.
        """
        while True:
            try:
                # Attempt to sync with network periodically
                if self.consensus_status == ConsensusStatus.SYNCING:
                    # Skip sync if in standalone mode
                    if self.standalone_mode or (hasattr(self, 'p2p') and self.p2p and self.p2p.standalone_mode):
                        logger.info("Standalone mode active, skipping network sync")
                        self.consensus_status = ConsensusStatus.PRODUCING if self.is_validator else ConsensusStatus.IDLE
                    else:
                        synced = await self.sync_with_network()
                        if synced:
                            # If we're synced, we can change state to IDLE or VALIDATING
                            self.consensus_status = ConsensusStatus.VALIDATING if self.is_validator else ConsensusStatus.IDLE
                        
                # Sleep for a while before next sync attempt
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                logger.info("State synchronizer task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in state synchronizer: {e}")
                await asyncio.sleep(30)  # Shorter sleep on error
                
    async def _validator_task(self):
        """
        Background task for validator nodes to produce blocks.
        """
        while True:
            try:
                # Check if we're the leader for the current slot
                if self.consensus_status == ConsensusStatus.VALIDATING:
                    slot_leader = self.select_validator()
                    if slot_leader == self.validator_address:
                        # We're the leader, produce a block
                        await self._produce_block(self.current_slot, self.current_epoch)
                
                # Sleep for a short time before checking again
                await asyncio.sleep(0.5)
                
            except asyncio.CancelledError:
                logger.info("Validator task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in validator task: {e}")
                await asyncio.sleep(5.0)

    async def _produce_block(self, slot, epoch):
        """
        Produce a new block as the leader for the current slot.
        
        Args:
            slot: Current slot number
            epoch: Current epoch number
            
        Returns:
            The newly created block if successful, None otherwise
        """
        try:
            logger.info(f"Producing block for slot {slot} in epoch {epoch}")
            
            # Get transactions from mempool
            with self.mempool_lock:
                pending_txs = list(self.mempool.values())
                
            # Sort transactions by fee (highest first)
            pending_txs.sort(key=lambda tx: tx.fee, reverse=True)
            
            # Limit to max transactions per block
            max_txs = 1000
            if len(pending_txs) > max_txs:
                pending_txs = pending_txs[:max_txs]
                
            # Get current PoH state
            poh_hash, poh_iterations, timestamp = self.poh.get_current_state()
            
            # Create new block
            with self.state_lock:
                new_block = Block(
                    height=len(self.blocks),
                    timestamp=int(time.time() * 1000),
                    prev_hash=self.chain_head.hash if self.chain_head else "0" * 64,
                    transactions=pending_txs,
                    validator=self.validator_address,
                    poh_hash=poh_hash.hex(),
                    poh_iterations=poh_iterations,
                    slot=slot,
                    epoch=epoch
                )
                
                # Sign the block
                if self.validator_key:
                    signature = self.validator_key.sign(new_block.get_message_for_signing())
                    new_block.signature = base64.b64encode(signature).decode()
                
                # Process the block
                success = await self.process_block(new_block)
                
                if success:
                    # Broadcast the new block to the network
                    await self.p2p.broadcast_new_block(new_block)
                    logger.info(f"Successfully produced and broadcast block {new_block.height}")
                    return new_block
                else:
                    logger.error(f"Failed to process new block at height {new_block.height}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error producing block: {e}")
            return None

    def lock_coins(self, address, amount, lock_period=DEFAULT_LOCK_PERIOD):
        """
        Lock coins for staking rewards.
        
        Args:
            address: Address to lock coins for
            amount: Amount to lock
            lock_period: Time to lock in seconds (default: 1 year)
            
        Returns:
            Dictionary with lock details if successful, error info if not
        """
        try:
            current_time = int(time.time())
            unlock_time = current_time + lock_period
            
            # Record the lock
            return {
                "success": True,
                "address": address,
                "amount": amount,
                "unlock_time": unlock_time
            }
            
        except Exception as e:
            logger.error(f"Error locking coins: {e}")
            return {"success": False, "error": str(e)}
    
    def get_slot_time(self, slot: int) -> float:
        """Get the expected time for a given slot."""
        return slot * SLOT_DURATION
        
    def get_current_slot(self) -> int:
        """Get the current slot based on current time."""
        # Start time is arbitrarily chosen as the beginning of 2023
        start_time = datetime.datetime(2023, 1, 1).timestamp()
        current_time = time.time()
        
        return int((current_time - start_time) / SLOT_DURATION)
    
    def get_total_stake(self) -> float:
        """Get the total stake across all validators."""
        return self.total_stake
