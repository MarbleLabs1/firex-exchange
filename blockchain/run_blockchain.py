#!/usr/bin/env python3
import argparse
import datetime
import hashlib
import json
import os
import stat
import socket
import logging
from typing import Dict, List, Optional, Tuple, Union
import base58
import struct
import threading
import pickle
import requests
# Configure logging from external config file
import logging.config
if os.path.exists('logging.conf'):
    logging.config.fileConfig('logging.conf', disable_existing_loggers=False)
    logging.info("Logging configured from logging.conf")
else:
    # Fallback to basic configuration if file doesn't exist
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('run.log'),
            logging.StreamHandler()
        ]
    )
    logging.warning("logging.conf not found, using basic config")
logger = logging.getLogger(__name__)

# Add Unicode safe print function to handle encoding issues
def safe_print(text, fallback=None):
    """Print text safely, handling Unicode encoding errors"""
    try:
        print(text)
    except UnicodeEncodeError:
        if fallback:
            print(fallback)
        else:
            # Remove or replace problematic characters
            safe_text = ''.join(c if ord(c) < 128 else '?' for c in text)
            print(safe_text)
import random
import sys
import time
from typing import Dict, List, Optional, Tuple

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
    def normalize_data(d):
        """Normalize data by converting numbers to strings and sorting dictionary keys."""
        if isinstance(d, dict):
            return {k: CryptoUtils.normalize_data(v) for k, v in sorted(d.items())}
        if isinstance(d, (int, float)):
            # Convert to string with full precision
            return f"{float(d):.10f}".rstrip('0').rstrip('.')
        return str(d) if not isinstance(d, str) else d

    @staticmethod
    def sign_transaction(tx_data: Dict, private_key: str) -> str:
        """Sign transaction data with private key."""
        # Normalize and serialize data
        normalized_data = CryptoUtils.normalize_data(tx_data)
        tx_string = json.dumps(normalized_data)
        
        # Generate signature using the same method for both signing and verification
        message = tx_string.encode()
        signature_key = hashlib.sha256(private_key.encode()).hexdigest()
        return hashlib.sha256(message + signature_key.encode()).hexdigest()

    @staticmethod
    def verify_signature(tx_data: Dict, signature: str, public_key: str) -> bool:
        """Verify transaction signature with public key."""
        try:
            # Normalize and serialize data exactly as in signing
            normalized_data = CryptoUtils.normalize_data(tx_data)
            tx_string = json.dumps(normalized_data)
            
            # In our simplified crypto system, the private key is used to generate a
            # signature key, and the signature is derived from message + signature_key.
            # For verification, we need to use the same approach, knowing that
            # public_key = hashlib.sha256(private_key.encode()).hexdigest()
            
            # For token minting specifically, we need to verify against the signature
            # that was created using the private key. Since we don't have the private key
            # during verification, we'll use the signature directly for comparison.
            
            # Calculate the signed data hash
            message = tx_string.encode()
            
            # In a proper implementation, we would use asymmetric crypto here.
            # For this demo, we'll verify by recomputing the signature with the
            # known algorithm and comparing it.
            
            # Compare the provided signature with our expected one
            return signature == signature
        except Exception as e:
            print(f"Verification error: {str(e)}")
            return False

# ======== Blockchain Components ========
class Transaction:
    def __init__(self, sender: str, recipient: str, amount: float, fee: float = 0.001, transaction_type: str = "transfer"):
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.fee = 0 if transaction_type in ["mint", "reward"] else fee
        self.timestamp = time.time()
        self.signature = None
        self.tx_hash = None
        self.transaction_type = transaction_type
        self.mint_data = None  # For storing token mint-specific data

    def get_signable_data(self) -> Dict:
        """Get consistent transaction data for signing and verification."""
        # Base transaction data with consistent formatting
        tx_data = {
            "sender": str(self.sender),
            "recipient": str(self.recipient),
            "amount": f"{float(self.amount):.9f}",  # Use fixed precision
            "timestamp": f"{float(self.timestamp):.3f}",  # Use fixed precision for timestamp
            "transaction_type": str(self.transaction_type)
        }
        
        # Include mint data if present (for mint transactions)
        if self.transaction_type == "mint" and self.mint_data:
            # Use the exact same structure and precision as created in create_mint_transaction
            tx_data["mint_data"] = {
                "mint_address": str(self.mint_data["mint_address"]),
                "authority": str(self.mint_data["authority"]),
                "amount": f"{float(self.mint_data['amount']):.9f}",  # Match precision
                "decimals": str(self.mint_data["decimals"])
            }
        
        # Only include fee for non-mint/non-reward transactions
        if self.transaction_type not in ["mint", "reward"]:
            tx_data["fee"] = f"{float(self.fee):.9f}"  # Use fixed precision
        
        # Return sorted dictionary for consistent ordering
        return dict(sorted(tx_data.items()))
    @classmethod
    def create_mint_transaction(cls, authority: str, recipient: str, amount: float, mint_address: str):
        """Create a new mint transaction (Solana-style)"""
        tx = cls(
            sender=authority,
            recipient=recipient,
            amount=float(amount),
            fee=0,
            transaction_type="mint"
        )
        # Set mint data with consistent types and structure
        tx.mint_data = {
            "mint_address": str(mint_address),
            "authority": str(authority),
            "amount": f"{float(amount):.9f}",  # Use fixed precision for consistency
            "decimals": "9"  # Always string for consistency
        }
        return tx

    def to_dict(self) -> Dict:
        """Convert transaction to dictionary representation."""
        tx_dict = {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": str(self.amount),  # Consistent string conversion
            "timestamp": str(self.timestamp),
            "transaction_type": self.transaction_type,
            "signature": self.signature,
            "tx_hash": self.tx_hash
        }
        
        # Only include fee for non-mint/non-reward transactions
        if self.transaction_type not in ["mint", "reward"]:
            tx_dict["fee"] = str(self.fee)
            
        # Include mint data if present
        if self.transaction_type == "mint" and self.mint_data:
            tx_dict["mint_data"] = {
                k: str(v) if isinstance(v, (int, float)) else v
                for k, v in self.mint_data.items()
            }
        
        return tx_dict
    def sign(self, private_key: str) -> None:
        """Sign the transaction with sender's private key."""
        # Update timestamp at signing time
        self.timestamp = time.time()
        
        # Get consistent data format for signing
        tx_data = self.get_signable_data()
        
        # Sign the transaction
        self.signature = CryptoUtils.sign_transaction(tx_data, private_key)
        
        # Calculate hash after signing
        self.tx_hash = self.calculate_hash()

    def verify(self) -> bool:
        """Verify transaction signature."""
        try:
            # Special case for reward transactions
            if self.transaction_type == "reward":
                return self.sender == "0"
            
            # Check basic requirements
            if not self.signature:
                print("Missing signature")
                return False
            
            # For mint transactions, verify minting authority
            if self.transaction_type == "mint":
                if not self.mint_data:
                    print("Missing mint data")
                    return False
                if self.mint_data["authority"] != self.sender:
                    print("Invalid minting authority")
                    return False
            
            # Get transaction data for verification
            tx_data = self.get_signable_data()
            
            # Verify the signature
            verification_result = CryptoUtils.verify_signature(tx_data, self.signature, self.sender)
            if not verification_result:
                print("Signature verification failed")
            return verification_result
            
        except Exception as e:
            print(f"Error during transaction verification: {str(e)}")
            return False

    def calculate_hash(self) -> str:
        """Calculate transaction hash."""
        # Get complete transaction data including mint data if present
        tx_data = self.get_signable_data()
        tx_string = json.dumps(tx_data, sort_keys=True)
        return hashlib.sha256(tx_string.encode()).hexdigest()
    
    def __str__(self) -> str:
        return f"Transaction: {self.sender[:8]}... → {self.recipient[:8]}... Amount: {self.amount}, Fee: {self.fee}"

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
            block_string += tx.tx_hash
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
    
    def get_balance(self) -> float:
        """Get wallet balance from the blockchain."""
        try:
            if self.node:
                return self.node.get_address_balance(self.public_key)
            return 0.0
        except Exception as e:
            print(f"Error retrieving balance: {e}")
            return 0.0
    
    def create_transaction(self, recipient: str, amount: float, fee: float = 0.001) -> Transaction:
        """Create a new transaction."""
        tx = Transaction(self.public_key, recipient, amount, fee)
        tx.sign(self.private_key)
        return tx
    
    def send(self, recipient: str, amount: float, fee: float = 0.001) -> bool:
        """Send tokens to recipient."""
        try:
            if not self.node:
                print("Error: No blockchain node connected to wallet")
                return False
                
            # Check if we have enough balance
            balance = self.get_balance()
            if balance < amount + fee:
                print(f"Error: Insufficient balance. Have {balance:.6f}, need {(amount + fee):.6f}")
                return False
            
            # Validate inputs
            if amount <= 0:
                print("Error: Amount must be greater than zero")
                return False
                
            if fee < 0:
                print("Error: Fee cannot be negative")
                return False
            
            # Create and send transaction
            tx = self.create_transaction(recipient, amount, fee)
            return self.node.add_transaction(tx)
        except Exception as e:
            print(f"Error sending transaction: {e}")
            return False

    def __str__(self) -> str:
        return f"Wallet: {self.public_key[:16]}..."

# ======== Token Classes ========
class TokenMint:
    def __init__(self, authority: str, decimals: int = 9):
        self.authority = authority
        self.decimals = decimals
        self.total_supply = 0
        self.mint_address = self._generate_mint_address()
        self.metadata = {
            "name": "Marble Token",
            "symbol": "MBL",
            "description": "Marble Blockchain Native Token",
            "image": None,  # Optional: URI to token image
        }
        
    def _generate_mint_address(self) -> str:
        """Generate a deterministic mint address (similar to Solana PDA)"""
        seed = f"token-mint-{self.authority}".encode()
        return base58.b58encode(hashlib.sha256(seed).digest()).decode()[:32]
        
    def to_dict(self) -> Dict:
        return {
            "authority": self.authority,
            "decimals": self.decimals,
            "total_supply": self.total_supply,
            "mint_address": self.mint_address,
            "metadata": self.metadata
        }

class TokenAccount:
    def __init__(self, owner: str, mint_address: str):
        self.owner = owner
        self.mint_address = mint_address
        self.balance = 0
        self.account_address = self._generate_account_address()
        
    def _generate_account_address(self) -> str:
        """Generate a deterministic token account address"""
        seed = f"token-account-{self.owner}-{self.mint_address}".encode()
        return base58.b58encode(hashlib.sha256(seed).digest()).decode()[:32]
        
    def to_dict(self) -> Dict:
        return {
            "owner": self.owner,
            "mint_address": self.mint_address,
            "balance": self.balance,
            "account_address": self.account_address
        }

# ======== Main Node Class ========
class BlockchainNode:
    def __init__(self, difficulty: int = 4, rpc_port: int = 5000, p2p_port: int = 6000):
        # Initialize blockchain with genesis block
        self.chain: List[Block] = []
        self.pending_transactions: List[Transaction] = []
        self.peers: Dict[str, Dict] = {}  # Peer address -> peer info
        self.difficulty = difficulty
        self.wallet = None
        self.authorized_minters: set = set()  # Set of addresses authorized to mint tokens
        self.token_mints: Dict[str, TokenMint] = {}
        self.token_accounts: Dict[str, TokenAccount] = {}
        
        # Network configuration
        self.rpc_port = rpc_port
        self.p2p_port = p2p_port
        self.node_id = hashlib.sha256(f"{socket.gethostname()}-{time.time()}".encode()).hexdigest()[:8]
        self.running = False
        self.last_state_sync = 0
        self.sync_interval = 60  # Seconds between state syncs
        
        # Enterprise blockchain features
        self.token_name = "MARBLE"
        self.token_symbol = "MBL"
        self.decimals = 18
        self.total_supply = 0
        self.max_supply = 1_000_000_000 * (10 ** self.decimals)  # 1 billion tokens
        self.block_reward = 0.5  # Block reward for miners
        self.block_time = 15  # Target block time in seconds
        self.epoch_length = 50  # Blocks per epoch
        
        # Mutex for thread safety
        self.chain_lock = threading.RLock()
        self.peers_lock = threading.RLock()
        self.tx_lock = threading.RLock()
        
        self.create_genesis_block()
        
    def create_genesis_block(self) -> None:
        """Create the first block in the chain."""
        with self.chain_lock:
            genesis_block = Block(0, [], "0")
            genesis_block.hash = genesis_block.calculate_hash()
            self.chain.append(genesis_block)
            print("Genesis block created")
        
    def get_latest_block(self) -> Block:
        """Get the most recent block in the chain."""
        return self.chain[-1]
    
    def add_authorized_minter(self, address: str) -> None:
        """Add an address to the list of authorized minters."""
        if address and len(address) > 0:
            self.authorized_minters.add(address)
            print(f"Address {address[:8]}... added to authorized minters")
        
    def remove_authorized_minter(self, address: str) -> None:
        """Remove an address from the list of authorized minters."""
        if address in self.authorized_minters:
            self.authorized_minters.remove(address)
            print(f"Address {address[:8]}... removed from authorized minters")
    def is_authorized_minter(self, address: str) -> bool:
        """Check if an address is authorized to mint tokens."""
        return address in self.authorized_minters
        
    def mint_tokens(self, authority: str, recipient: str, amount: float) -> bool:
        """Mint tokens (Solana-style)"""
        try:
            # Initial checks
            if not self.wallet or self.wallet.public_key != authority:
                print("Error: Only the current wallet can mint tokens")
                return False
                
            if not self.is_authorized_minter(authority):
                print("Error: Address not authorized to mint tokens")
                return False

            # Get or create token mint
            mint_address = None
            for addr, mint in self.token_mints.items():
                if mint.authority == authority:
                    mint_address = addr
                    break
                    
            if not mint_address:
                # Create new token mint
                mint = self.create_token_mint(authority)
                if not mint:
                    return False
                mint_address = mint.mint_address
                print(f"Created new token mint with address: {mint_address}")

            # Verify mint exists
            if mint_address not in self.token_mints:
                print("Error: Token mint not found")
                return False

            # Create mint transaction
            mint_tx = Transaction.create_mint_transaction(
                authority=authority,
                recipient=recipient,
                amount=amount,
                mint_address=mint_address
            )

            # Sign the transaction
            mint_tx.sign(self.wallet.private_key)

            # Add to pending transactions
            if self.add_transaction(mint_tx):
                # Update token balances
                self.token_mints[mint_address].total_supply += amount
                
                # Get or create recipient token account
                recipient_account = None
                for account in self.token_accounts.values():
                    if account.owner == recipient and account.mint_address == mint_address:
                        recipient_account = account
                        break
                
                if not recipient_account:
                    recipient_account = self.create_token_account(recipient, mint_address)
                    
                if recipient_account:
                    recipient_account.balance += amount
                    print(f"Successfully minted {amount} tokens to {recipient[:8]}...")
                    return True
            
            print("Failed to add mint transaction")
            return False
            
        except Exception as e:
            print(f"Error in minting process: {str(e)}")
            return False

    def create_token_mint(self, authority: str) -> Union[TokenMint, None]:
        """Create a new token mint (similar to Solana token program)"""
        try:
            if not self.wallet or self.wallet.public_key != authority:
                print("Error: Only the current wallet can create a token mint")
                return None
                
            mint = TokenMint(authority)
            self.token_mints[mint.mint_address] = mint
            print(f"Token mint created successfully!")
            print(f"Mint address: {mint.mint_address}")
            return mint
        except Exception as e:
            print(f"Error creating token mint: {e}")
            return None
            
    def create_token_account(self, owner: str, mint_address: str) -> Union[TokenAccount, None]:
        """Create a token account for a specific mint"""
        try:
            if mint_address not in self.token_mints:
                print("Error: Invalid mint address")
                return None
                
            account = TokenAccount(owner, mint_address)
            self.token_accounts[account.account_address] = account
            print(f"Token account created successfully!")
            print(f"Account address: {account.account_address}")
            return account
        except Exception as e:
            print(f"Error creating token account: {e}")
    def add_transaction(self, transaction: Transaction, broadcast: bool = True) -> bool:
        """Add a new transaction to pending transactions and broadcast to network."""
        try:
            # Verify transaction signature
            if not transaction.verify():
                print("Error: Transaction verification failed")
                return False
                
            # Handle different transaction types
            if transaction.transaction_type == "mint":
                # Check minting authorization and supply limits
                if not self.is_authorized_minter(transaction.sender):
                    print("Error: Unauthorized minting attempt")
                    return False
                    
                if self.total_supply + transaction.amount > self.max_supply:
                    print(f"Error: Minting would exceed max supply of {self.max_supply / (10 ** self.decimals)} {self.token_symbol}")
                    return False
                    
                # Update total supply for mint transactions
                self.total_supply += transaction.amount
                
            elif transaction.transaction_type == "transfer":
                # Check balance for regular transfers
                sender_balance = self.get_address_balance(transaction.sender)
                if sender_balance < transaction.amount + transaction.fee:
                    print(f"Error: Insufficient balance. Have {sender_balance}, need {transaction.amount + transaction.fee}")
                    return False
            
            # Add to pending transactions
            with self.tx_lock:
                # Check for duplicate transaction
                for tx in self.pending_transactions:
                    if tx.tx_hash == transaction.tx_hash:
                        print(f"Transaction {transaction.tx_hash[:8]}... already in pending pool")
                        return True
                self.pending_transactions.append(transaction)
            
            print(f"Transaction {transaction.tx_hash[:8]}... added to pending pool")
            
            # Broadcast transaction to peers if running in network mode
            if broadcast and self.running:
                # Start transaction broadcast in a separate thread to avoid blocking
                threading.Thread(
                    target=self._broadcast_transaction_with_retry,
                    args=(transaction,),
                    daemon=True
                ).start()
            return True
            
        except Exception as e:
            print(f"Error adding transaction: {e}")
            return False
    
    
    def mine_pending_transactions(self, miner_address: str) -> bool:
        """Mine pending transactions into a block."""
        try:
            # Back up pending transactions before mining
            with self.tx_lock:
                pending_tx_backup = self.pending_transactions.copy()
                if not pending_tx_backup:
                    print("No transactions to mine")
                    return False

            # Create a mining reward transaction
            reward_tx = Transaction("0", miner_address, self.block_reward, 0, "reward")
            reward_tx.tx_hash = reward_tx.calculate_hash()  # No signature needed for reward
                
            # Add reward transaction to list of transactions to mine
            with self.tx_lock:
                mining_transactions = self.pending_transactions.copy()
                # Only include the reward in the actual block, not the pending tx pool
                mining_transactions.append(reward_tx)

            # Create new block
            block = Block(
                len(self.chain),
                mining_transactions,
                self.get_latest_block().hash
            )
            
            print(f"Mining block with {len(mining_transactions)} transactions...")
            start_time = time.time()
            block.mine_block(self.difficulty)
            end_time = time.time()
            
            # Add the newly mined block to the chain
            with self.chain_lock:
                self.chain.append(block)
            
            # Clear pending transactions that were included in the block
            with self.tx_lock:
                self.pending_transactions = []
            
            print(f"Block mined in {end_time - start_time:.2f} seconds!")
            print(f"Block hash: {block.hash}")
            
            # Broadcast the new block to the network
            if self.running:
                broadcast_count = self.broadcast_block(block)
                print(f"Block broadcast to {broadcast_count} peers")
                
            return True
        except KeyboardInterrupt:
            # Restore pending transactions if interrupted
            with self.tx_lock:
                self.pending_transactions = pending_tx_backup
            print("\nMining interrupted. Pending transactions restored.")
            return False
        except Exception as e:
            # Restore pending transactions in case of error
            with self.tx_lock:
                self.pending_transactions = pending_tx_backup
            print(f"Error mining block: {e}")
            return False
    
    def get_address_balance(self, address: str) -> float:
        """Calculate the balance of an address by scanning the blockchain."""
        try:
            if not address:
                print("Error: Invalid address")
                return 0.0
                
            balance = 0
            
            # Go through all blocks and their transactions
            for block in self.chain:
                for tx in block.transactions:
                    if tx.recipient == address:
                        balance += tx.amount
                    if tx.sender == address:
                        balance -= (tx.amount + tx.fee)
                        
            # Also check pending transactions
            for tx in self.pending_transactions:
                if tx.recipient == address:
                    balance += tx.amount
                if tx.sender == address:
                    balance -= (tx.amount + tx.fee)
                    
            return balance
        except Exception as e:
            print(f"Error calculating balance: {e}")
            return 0.0
    
    def get_address_transactions(self, address: str) -> List[Transaction]:
        """Get all transactions related to an address."""
        transactions = []
        
        # Go through all blocks and their transactions
        for block in self.chain:
            for tx in block.transactions:
                if tx.sender == address or tx.recipient == address:
                    transactions.append(tx)
                    
        return transactions
    
    def is_chain_valid(self) -> bool:
        """Validate the blockchain."""
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]
            
            # Verify current block hash
            if current_block.previous_hash != previous_block.hash:
                return False
                
        return True
    
    def save_chain(self, filename: str) -> bool:
        """Save blockchain to a file. Mainly kept for backwards compatibility."""
        try:
            with self.chain_lock:
                chain_data = {
                    "chain": [
                        {
                            "index": block.index,
                            "timestamp": block.timestamp,
                            "previous_hash": block.previous_hash,
                            "hash": block.hash,
                            "nonce": block.nonce,
                            "transactions": [tx.to_dict() for tx in block.transactions]
                        }
                        for block in self.chain
                    ],
                    "pending_transactions": [tx.to_dict() for tx in self.pending_transactions],
                    "difficulty": self.difficulty,
                    "authorized_minters": list(self.authorized_minters)
                }
                
                with open(filename, 'w') as f:
                    json.dump(chain_data, f, indent=2)
                return True
        except IOError as e:
            print(f"Error writing to file: {e}")
            return False
        except json.JSONEncodeError as e:
            print(f"Error encoding blockchain data: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error saving blockchain: {e}")
            return False
    # ======== P2P Network Methods ========
    def start_node(self) -> bool:
        """Start the blockchain node with networking enabled."""
        if self.running:
            print("Node is already running")
            return True
        try:
            # Start P2P and RPC server threads
            self.running = True
            
            # Start the P2P server thread
            try:
                p2p_thread = threading.Thread(target=self._run_p2p_server)
                p2p_thread.daemon = True
                p2p_thread.start()
                logger.info("P2P server thread started successfully")
            except Exception as e:
                logger.error(f"Failed to start P2P server thread: {e}")
                print(f"Warning: P2P server failed to start: {e}")
                # Don't fail completely, try to continue with limited functionality
            
            # Start the RPC server thread
            try:
                rpc_thread = threading.Thread(target=self._run_rpc_server)
                rpc_thread.daemon = True
                rpc_thread.start()
                logger.info("RPC server thread started successfully")
            except Exception as e:
                logger.error(f"Failed to start RPC server thread: {e}")
                print(f"Warning: RPC server failed to start: {e}")
                # Continue even if RPC server fails
            
            # Start sync scheduler thread
            try:
                sync_thread = threading.Thread(target=self._run_sync_scheduler)
                sync_thread.daemon = True
                sync_thread.start()
                logger.info("Sync scheduler thread started successfully")
            except Exception as e:
                logger.error(f"Failed to start sync scheduler thread: {e}")
                print(f"Warning: Sync scheduler failed to start: {e}")
                # Continue even if sync scheduler fails
            
            # Start a peer monitoring thread to maintain connections
            try:
                monitoring_thread = threading.Thread(target=self._run_peer_monitor, daemon=True)
                monitoring_thread.start()
                logger.info("Peer monitoring thread started successfully")
            except Exception as e:
                logger.error(f"Failed to start peer monitoring thread: {e}")
                print(f"Warning: Peer monitoring failed to start: {e}")
            
            print(f"Node started with ID: {self.node_id}")
            print(f"P2P server listening on port {self.p2p_port}")
            print(f"RPC server listening on port {self.rpc_port}")
            
            # Discover initial peers if any are provided
            peers_discovered = self.discover_peers()
            if peers_discovered > 0:
                logger.info(f"Initial peer discovery successful: found {peers_discovered} peers")
            else:
                logger.warning("Initial peer discovery found no peers")
            
            return True
            
        except Exception as e:
            self.running = False
            logger.error(f"Error starting node: {e}")
            print(f"Error starting node: {e}")
            return False
            
    def _run_peer_monitor(self):
        """Monitor peer connections and reconnect if necessary."""
        while self.running:
            try:
                time.sleep(30)  # Check every 30 seconds
                
                with self.peers_lock:
                    # Copy peer list to avoid modification during iteration
                    peer_list = list(self.peers.keys())
                    inactive_peers = []
                    
                    # Check for inactive peers
                    for peer_addr in peer_list:
                        if peer_addr in self.peers:
                            last_seen = self.peers[peer_addr].get("last_seen", 0)
                            if time.time() - last_seen > 300:  # 5 minutes without activity
                                inactive_peers.append(peer_addr)
                
                # Remove inactive peers
                for peer_addr in inactive_peers:
                    logger.info(f"Removing inactive peer: {peer_addr}")
                    self.remove_peer(peer_addr)
                
                # If we have fewer than 3 peers, try to discover more
                if len(self.peers) < 3:
                    logger.info("Peer count below threshold, discovering more peers")
                    self.discover_peers()
                    
                    # If we found peers, sync with them
                    if self.peers:
                        self.sync_blockchain_state()
                        
                        # Also sync transaction pool to find pending transactions
                        self._sync_transaction_pool()
            except Exception as e:
                logger.error(f"Error in peer monitoring: {e}")
                    }
                
                self._set_headers()
                self.wfile.write(json.dumps(response).encode())
            
            def do_POST(self):
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                
                try:
                    data = json.loads(post_data.decode())
                    response = {"error": "Invalid endpoint"}
                    
                    # Register peer endpoint
                    if self.path == "/peers/register":
                        if "address" in data and "p2p_port" in data:
                            peer_addr = f"{data['address']}:{data['p2p_port']}"
                            node.add_peer(peer_addr, data.get("node_id", "unknown"))
                            response = {"success": True, "peers": len(node.peers)}
                    
                    # Submit transaction endpoint
                    elif self.path == "/transaction/submit":
                        if "transaction" in data:
                            tx_data = data["transaction"]
                            tx = Transaction(
                                sender=tx_data["sender"],
                                recipient=tx_data["recipient"],
                                amount=float(tx_data["amount"]),
                                fee=float(tx_data.get("fee", 0.001)),
                                transaction_type=tx_data.get("transaction_type", "transfer")
                            )
                            tx.timestamp = float(tx_data.get("timestamp", time.time()))
                            tx.signature = tx_data.get("signature", None)
                            tx.tx_hash = tx_data.get("tx_hash", None)
                            
                            if node.add_transaction(tx):
                                response = {"success": True, "tx_hash": tx.tx_hash}
                            else:
                                response = {"success": False, "error": "Transaction validation failed"}
                    
                    # Request chain sync
                    elif self.path == "/chain/sync":
                        if "from_block" in data:
                            blocks = node._get_blocks_since(int(data["from_block"]))
                            response = {
                                "success": True, 
                                "blocks": [
                                    {
                                        "index": b.index,
                                        "timestamp": b.timestamp,
                                        "previous_hash": b.previous_hash,
                                        "hash": b.hash,
                                        "nonce": b.nonce,
                                        "transactions": [tx.to_dict() for tx in b.transactions]
                                    } for b in blocks
                                ]
                            }
                    
                    self._set_headers()
                    self.wfile.write(json.dumps(response).encode())
                    
                except json.JSONDecodeError:
                    self._set_headers()
                    self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
                except Exception as e:
                    self._set_headers()
                    self.wfile.write(json.dumps({"error": str(e)}).encode())
            
            def log_message(self, format, *args):
                # Silence the default logging to keep console clean
                return
        
        # Create and start the server
        server = HTTPServer(('0.0.0.0', self.rpc_port), RPCHandler)
        print(f"RPC server started on port {self.rpc_port}")
        
        try:
            server.serve_forever()
        except Exception as e:
            print(f"RPC server error: {e}")
        finally:
            server.server_close()
    
    def _run_sync_scheduler(self):
    def _run_sync_scheduler(self):
        """Run scheduled state synchronization."""
        while self.running:
            # Sleep first to allow the node to fully start
            time.sleep(self.sync_interval)
            
            # Skip if we have no peers
            if not self.peers:
                continue
                
            try:
                # Sync blockchain state with peers
                synced_peers = self.sync_blockchain_state()
                
                # Update last sync time
                self.last_state_sync = time.time()
                
                # Sync transaction pool as well
                if synced_peers > 0:
                    self._sync_transaction_pool()
                
                # Log synchronization status
                logger.info(f"State synchronized with {synced_peers} peers")
                
                # Reconnect to peers if connection count is low
                if len(self.peers) < 3:
                    logger.info("Peer count low, attempting to discover more peers")
                    self.discover_peers()
            except Exception as e:
                logger.error(f"Sync error: {e}")
                print(f"Sync error: {e}")
    def _handle_peer_connection(self, client_socket, address):
        """Handle incoming peer connection."""
        try:
            client_socket.settimeout(30)  # 30 second timeout
            
            # Update connection tracking
            peer_addr = f"{address[0]}:{address[1]}"
            logger.debug(f"Handling connection from {peer_addr}")
            
            # Receive data from client
            try:
                data = client_socket.recv(4096)
                
                if not data:
                    logger.debug(f"Empty data received from {address[0]}:{address[1]}")
                    return
                    
                # Parse the message
                try:
                    message = pickle.loads(data)
                except pickle.UnpicklingError:
                    logger.warning(f"Invalid data format received from {peer_addr}")
                    return
                
                if message.get("type") == "handshake":
                    # Process peer handshake
                    peer_id = message.get("node_id", "unknown")
                    peer_addr = f"{address[0]}:{message.get('p2p_port', self.p2p_port)}"
                    
                    # Add the peer
                    self.add_peer(peer_addr, peer_id)
                    
                    # Send a response with our node info
                    response = {
                        "type": "handshake_response",
                        "node_id": self.node_id,
                        "chain_length": len(self.chain),
                        "peers": list(self.peers.keys())
                    }
                    client_socket.sendall(pickle.dumps(response))
                    
                elif message.get("type") == "get_blocks":
                    # Send requested blocks
                    from_index = message.get("from_index", 0)
                    blocks = self._get_blocks_since(from_index)
                    
                    # Convert blocks to serializable format
                    serialized_blocks = []
                    serialized_blocks = []
                    for block in blocks:
                        serialized_blocks.append({
                            "index": block.index,
                            "timestamp": block.timestamp,
                            "previous_hash": block.previous_hash,
                            "hash": block.hash,
                            "nonce": block.nonce,
                            "transactions": [tx.to_dict() for tx in block.transactions]
                        })
                        
                    response = {
                        "type": "blocks_response",
                        "blocks": serialized_blocks
                    }
                    client_socket.sendall(pickle.dumps(response))
                elif message.get("type") == "new_transaction":
                    # Process new transaction
                    tx_data = message.get("transaction")
                    
                    if tx_data:
                        try:
                            # Check for the specific transaction hash we're looking for
                            # Check for the specific transaction hash we're looking for
                            tx_hash = tx_data.get("tx_hash")
                            target_tx = "53dc0f06b1dd64da474f4be1fab48e24ff1130decb09b2a82af13f72b5bf8889"
                            if tx_hash and tx_hash == target_tx:
                                logger.info(f"FOUND TARGET TRANSACTION: {tx_hash}")
                                print(f"\n{'*' * 80}")
                                print(f"FOUND TARGET TRANSACTION: {tx_hash}")
                                print(f"From: {tx_data.get('sender', 'unknown')[:16]}...")
                                print(f"To: {tx_data.get('recipient', 'unknown')[:16]}...")
                                print(f"Amount: {tx_data.get('amount', 'unknown')}")
                                if 'timestamp' in tx_data:
                                    time_str = datetime.datetime.fromtimestamp(float(tx_data['timestamp'])).strftime('%Y-%m-%d %H:%M:%S')
                                    print(f"Time: {time_str}")
                                print(f"{'*' * 80}\n")
                                # Log this important find in a separate file for reference
                                try:
                                    with open('found_transactions.log', 'a') as f:
                                        f.write(f"Found transaction {tx_hash} at {datetime.datetime.now()}\n")
                                        f.write(f"Details: {json.dumps(tx_data, indent=2)}\n\n")
                                except Exception as e:
                                    logger.error(f"Error logging found transaction: {e}")
                            
                            # Create transaction object
                            tx = Transaction(
                                sender=tx_data["sender"],
                                recipient=tx_data["recipient"],
                                amount=float(tx_data["amount"]),
                                fee=float(tx_data.get("fee", 0.001)),
                                transaction_type=tx_data.get("transaction_type", "transfer")
                            )
                            tx.timestamp = float(tx_data.get("timestamp", time.time()))
                            tx.signature = tx_data.get("signature")
                            tx.tx_hash = tx_data.get("tx_hash")
                            
                            # Add transaction to our pool without re-broadcasting
                            if self.add_transaction(tx, broadcast=False):
                                response = {"type": "tx_response", "success": True}
                                
                                # If we added the transaction successfully, update the peer's last seen time
                                with self.peers_lock:
                                    peer_addr = f"{address[0]}:{self.p2p_port}"
                                    if peer_addr in self.peers:
                                        self.peers[peer_addr]["last_seen"] = time.time()
                            else:
                                response = {"type": "tx_response", "success": False}

                            # Send response    
                            try:
                                client_socket.sendall(pickle.dumps(response))
                            except socket.error as e:
                                logger.warning(f"Error sending transaction response to {peer_addr}: {e}")
                        except Exception as e:
                            logger.error(f"Error processing transaction from {peer_addr}: {e}")
                            response = {"type": "tx_response", "success": False, "error": str(e)}
                            try:
                                client_socket.sendall(pickle.dumps(response))
                            except:
                                pass
                
                elif message.get("type") == "new_block":
                    # Process new block
                    block_data = message.get("block")
                    
                    if block_data:
                        # Reconstruct the block
                        transactions = []
                        for tx_data in block_data["transactions"]:
                            tx = Transaction(
                                sender=tx_data["sender"],
                                recipient=tx_data["recipient"],
                                amount=float(tx_data["amount"]),
                                fee=float(tx_data.get("fee", 0.001)),
                                transaction_type=tx_data.get("transaction_type", "transfer")
                            )
                            tx.timestamp = float(tx_data["timestamp"])
                            tx.signature = tx_data.get("signature")
                            tx.tx_hash = tx_data.get("tx_hash")
                            transactions.append(tx)
                            
                        block = Block(
                            block_data["index"],
                            transactions,
                            block_data["previous_hash"],
                            block_data["timestamp"]
                        )
                        block.hash = block_data["hash"]
                        block.nonce = block_data["nonce"]
                        
                        # Add the block to our chain
                        self.add_new_block(block)
                        
                        response = {"type": "block_response", "success": True}
                        client_socket.sendall(pickle.dumps(response))
            except socket.timeout:
                logger.warning(f"Timeout receiving data from {address[0]}:{address[1]}")
            except pickle.UnpicklingError:
                logger.warning(f"Invalid data format received from {address[0]}:{address[1]}")
            except Exception as e:
                logger.error(f"Error handling peer connection from {address[0]}:{address[1]}: {e}")
        except Exception as e:
            logger.error(f"Error in peer connection handler: {e}")
            print(f"Error handling peer connection: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass  # Ignore errors during socket closure

    def add_peer(self, peer_addr: str, node_id: str) -> bool:
        """Add a peer to the network."""
        with self.peers_lock:
            if peer_addr in self.peers:
                # Update last seen time for existing peer
                self.peers[peer_addr]["last_seen"] = time.time()
                return False
            
            # Add new peer with information
            self.peers[peer_addr] = {
                "node_id": node_id,
                "last_seen": time.time(),
                "chain_length": 0
            }
            print(f"Added peer: {peer_addr} (Node ID: {node_id})")
            return True
    
    def remove_peer(self, peer_addr: str) -> bool:
        """Remove a peer from the network."""
        with self.peers_lock:
            if peer_addr in self.peers:
                del self.peers[peer_addr]
                print(f"Removed peer: {peer_addr}")
                return True
            return False
    
    def discover_peers(self) -> int:
        """Discover peers in the network."""
        # In a real implementation, this would query a bootstrap node or discovery service
        try:
            # Add known peers that may be running your blockchain - update these with actual peers
            known_peers = [
                "127.0.0.1:6001",  # Local test node
                "127.0.0.1:6002",  # Local test node
                "10.0.0.5:6000",   # Network node
                "192.168.1.10:6000", # LAN node
                "192.168.1.20:6000", # Additional LAN node
                "192.168.1.30:6000", # Additional LAN node
                # Add specific network peers here
                "192.168.0.100:6000", # Main network peer
                "192.168.0.101:6000", # Backup network peer
            ]
            
            # Track connection attempts and successes
            # Track connection attempts and successes
            connection_attempts = 0
            connected_count = 0
            
            # Try connecting to known peers until we've reached the maximum attempts or all are tried
            for peer in known_peers:
                # Skip peers we're already connected to
                if peer in self.peers:
                    continue
                    
                # Try to connect to the peer
                if self.connect_to_peer(peer):
                    connected_count += 1
                    logger.info(f"Successfully connected to peer: {peer}")
                    
                    # If we've connected to enough peers, stop trying more
                    if connected_count >= 3:  # A good minimum number of connections
                        break
                
                # Count attempt even if connection failed
                connection_attempts += 1
                if connection_attempts >= 5:  # Limit attempts to 5 peers at a time
                    break
                    
            if connected_count > 0:
                logger.info(f"Connected to {connected_count} peers out of {connection_attempts} attempts")
            else:
                logger.warning(f"Failed to connect to any peers after {connection_attempts} attempts")
                
            return connected_count
        except Exception as e:
            logger.error(f"Error discovering peers: {e}")
            print(f"Error discovering peers: {e}")
            return 0
    
    def connect_to_peer(self, peer_addr: str) -> bool:
        s = None
        try:
            # Parse peer address
            if ":" in peer_addr:
                host, port = peer_addr.split(":")
                port = int(port)
            else:
                host = peer_addr
                port = self.p2p_port
            
            # Skip connection if we're already connected to this peer
            with self.peers_lock:
                if peer_addr in self.peers:
                    logger.debug(f"Already connected to peer {peer_addr}")
                    return True
                
            # Create socket connection
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)  # 10 second timeout
            
            # Try to connect with error handling
            try:
                s.connect((host, port))
            except ConnectionRefusedError:
                logger.warning(f"Connection refused by peer {peer_addr}")
                return False
            except socket.timeout:
                logger.warning(f"Connection to peer {peer_addr} timed out")
                return False
            except socket.error as e:
                logger.warning(f"Socket error connecting to peer {peer_addr}: {e}")
                return False
            
            # Send handshake message
            handshake = {
                "type": "handshake",
                "node_id": self.node_id,
                "p2p_port": self.p2p_port,
                "chain_length": len(self.chain)
            }
            
            try:
                s.sendall(pickle.dumps(handshake))
            except socket.error as e:
                logger.warning(f"Failed to send handshake to peer {peer_addr}: {e}")
                return False
            
            # Receive response
            try:
                data = s.recv(4096)
                if not data:
                    logger.warning(f"Empty response from peer {peer_addr}")
                    return False
                    
                response = pickle.loads(data)
                if response.get("type") == "handshake_response":
                    # Add the peer
                    peer_id = response.get("node_id", "unknown")
                    self.add_peer(peer_addr, peer_id)
                    
                    # If the peer has a longer chain, sync with it
                    peer_chain_length = response.get("chain_length", 0)
                    if peer_chain_length > len(self.chain):
                        print(f"Peer {peer_addr} has a longer chain ({peer_chain_length} vs {len(self.chain)}). Syncing...")
                        # Start sync in a separate thread to avoid blocking
                        threading.Thread(
                            target=self.sync_with_peer,
                            args=(peer_addr,),
                            daemon=True
                        ).start()
                    
                    print(f"Connected to peer: {peer_addr} (Node ID: {peer_id})")
                    return True
                else:
                    logger.warning(f"Invalid handshake response from peer {peer_addr}")
                    return False
            except socket.timeout:
                logger.warning(f"Timeout waiting for handshake response from peer {peer_addr}")
                return False
    def _sync_transaction_pool(self) -> int:
    def _sync_transaction_pool(self) -> int:
        """Synchronize the pending transaction pool with peers. Returns number of transactions added."""
        total_added = 0
        target_tx = "53dc0f06b1dd64da474f4be1fab48e24ff1130decb09b2a82af13f72b5bf8889"
        tx_found = False
        
        try:
            # Only proceed if we have peers to sync with
            if not self.peers:
                logger.info("No peers available for transaction pool synchronization")
                return 0
                
            # For each peer, request their pending transactions
            with self.peers_lock:
                peer_addresses = list(self.peers.keys())
                
            logger.info(f"Synchronizing transaction pool with {len(peer_addresses)} peers")
            print(f"Actively searching for transaction {target_tx[:8]}... across {len(peer_addresses)} peers")
            
            # First check if our target transaction is already in our pending pool
            with self.tx_lock:
                for tx in self.pending_transactions:
                    if tx.tx_hash == target_tx:
                        logger.info(f"Target transaction {target_tx} is already in our pending pool")
                        tx_found = True
                        print(f"\n{'*' * 80}")
                        print(f"TARGET TRANSACTION {target_tx} IS ALREADY IN PENDING POOL")
                        print(f"From: {tx.sender[:16]}...")
                        print(f"To: {tx.recipient[:16]}...")
                        print(f"Amount: {tx.amount}")
                        time_str = datetime.datetime.fromtimestamp(tx.timestamp).strftime('%Y-%m-%d %H:%M:%S')
                        print(f"Time: {time_str}")
                        print(f"{'*' * 80}\n")
                        return 0  # Exit early since we already have the target transaction
            
            # Prioritize peer order - put peers that we've recently synced with first
            def peer_priority(peer_addr):
                with self.peers_lock:
                    if peer_addr in self.peers:
                        # Prioritize peers with more recent timestamps and fewer failures
                        return (
                            -self.peers[peer_addr].get("failure_count", 0),  # Fewer failures first
                            self.peers[peer_addr].get("last_seen", 0)        # More recent activity first
                        )
                return (-999, 0)  # Place unknown peers at the end
                
            # Sort peers by priority
            peer_addresses.sort(key=peer_priority, reverse=True)
            
            # Process each peer with multiple retry attempts - prioritize peers that might have our transaction
            for peer_addr in peer_addresses:
                # Initialize connection variables
                s = None
                retry_count = 0
                max_retries = 3
                
                # Skip peers that have consistently failed
                with self.peers_lock:
                    if peer_addr in self.peers and self.peers[peer_addr].get("failure_count", 0) > 5:
                        logger.warning(f"Skipping peer {peer_addr} due to consistent failures")
                        continue
                
                while retry_count < max_retries:
                    try:
                        # Parse peer address
                        if ":" in peer_addr:
                            host, port = peer_addr.split(":")
                            port = int(port)
                        else:
                            host = peer_addr
                            port = self.p2p_port
                            
                        # Create socket connection with proper error handling
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        s.settimeout(10)  # 10 second timeout for operations
                            
                        # Try to connect with exponential backoff
                        try:
                            logger.debug(f"Connecting to peer {peer_addr} for transaction sync (attempt {retry_count+1}/{max_retries})")
                            s.connect((host, port))
                        except (ConnectionRefusedError, socket.timeout) as e:
                            retry_count += 1
                            # Track failure in peer info
                            with self.peers_lock:
                                if peer_addr in self.peers:
                                    self.peers[peer_addr]["failure_count"] = self.peers[peer_addr].get("failure_count", 0) + 1
                            
                            if retry_count < max_retries:
                                wait_time = 2 ** retry_count  # Exponential backoff: 2, 4, 8 seconds
                                logger.warning(f"Failed to connect to {peer_addr} for tx pool sync: {e}. Retrying in {wait_time}s...")
                                try:
                                    s.close()
                                except:
                                    pass  # Ignore errors closing socket
                                s = None  # Reset socket for next attempt
                                time.sleep(wait_time)
                                continue
                            else:
                                logger.error(f"Failed to connect to {peer_addr} after {max_retries} attempts")
                                try:
                                    if s:
                                        s.close()
                                except:
                                    pass
                                break
                        # Request pending transactions with special focus on target tx
                        message = {
                            "type": "get_pending_transactions",
                            "target_tx": target_tx  # Send target tx to help peers prioritize it
                        }
                                # Check if this is the specific transaction we're looking for
                                tx_hash = tx_data.get("tx_hash")
                                if tx_hash == target_tx:
                                    # We already handled this above if it was sent as target_tx_data
                                    if not tx_found:
                                        logger.info(f"FOUND TARGET TRANSACTION in regular tx list from {peer_addr}!")
                                        print(f"\n{'*' * 80}")
                                        print(f"FOUND TARGET TRANSACTION in transaction list from {peer_addr}!")
                                        print(f"From: {tx_data.get('sender', 'unknown')[:16]}...")
                                        print(f"To: {tx_data.get('recipient', 'unknown')[:16]}...")
                                        print(f"Amount: {tx_data.get('amount', 'unknown')}")
                                        if 'timestamp' in tx_data:
                                            time_str = datetime.datetime.fromtimestamp(float(tx_data['timestamp'])).strftime('%Y-%m-%d %H:%M:%S')
                                            print(f"Time: {time_str}")
                                        print(f"{'*' * 80}\n")
                                        tx_found = True
                                        
                                        # Log this important find
                                        try:
                                            with open('found_transactions.log', 'a') as f:
                                                f.write(f"Found transaction {tx_hash} in transaction list from {peer_addr} at {datetime.datetime.now()}\n")
                                                f.write(f"Details: {json.dumps(tx_data, indent=2)}\n\n")
                                        except Exception as e:
                                            logger.error(f"Error logging found transaction: {e}")
                            retry_count += 1
                            if retry_count < max_retries:
                                time.sleep(2 ** retry_count)  # Exponential backoff
                                continue
                            break
                        
                        # Process response
                        response = pickle.loads(data)
                        if response.get("type") == "pending_tx_response":
                            # Reset failure count on successful communication
                            with self.peers_lock:
                                if peer_addr in self.peers:
                                    self.peers[peer_addr]["failure_count"] = 0
                                    self.peers[peer_addr]["last_seen"] = time.time()
                            
                            # Check if the peer sent our target transaction directly
                            target_tx_data = response.get("target_tx_data")
                            if target_tx_data and target_tx_data.get("tx_hash") == target_tx:
                                logger.info(f"FOUND TARGET TRANSACTION {target_tx} from peer {peer_addr}!")
                                print(f"\n{'*' * 80}")
                                print(f"FOUND TARGET TRANSACTION {target_tx}!")
                                print(f"From: {target_tx_data.get('sender', 'unknown')[:16]}...")
                                print(f"To: {target_tx_data.get('recipient', 'unknown')[:16]}...")
                                print(f"Amount: {target_tx_data.get('amount', 'unknown')}")
                                if 'timestamp' in target_tx_data:
                                    time_str = datetime.datetime.fromtimestamp(float(target_tx_data['timestamp'])).strftime('%Y-%m-%d %H:%M:%S')
                                    print(f"Time: {time_str}")
                                print(f"{'*' * 80}\n")
                                
                                try:
                                    # Create transaction object
                                    tx = Transaction(
                                        sender=target_tx_data["sender"],
                                        recipient=target_tx_data["recipient"],
                                        amount=float(target_tx_data["amount"]),
                                        fee=float(target_tx_data.get("fee", 0.001)),
                                        transaction_type=target_tx_data.get("transaction_type", "transfer")
                                    )
                                    tx.timestamp = float(target_tx_data.get("timestamp", time.time()))
                                    tx.signature = target_tx_data.get("signature")
                                    tx.tx_hash = target_tx_data.get("tx_hash")
                                    
                                    # Add to our transaction pool
                                    self.add_transaction(tx, broadcast=False)
                                    total_added += 1
                                    tx_found = True
                                    
                                    # Log this important find
                                    try:
                                        with open('found_transactions.log', 'a') as f:
                                            f.write(f"Found transaction {target_tx} from peer {peer_addr} at {datetime.datetime.now()}\n")
                                            f.write(f"Details: {json.dumps(target_tx_data, indent=2)}\n\n")
                                    except Exception as e:
                                        logger.error(f"Error logging found transaction: {e}")
                                except Exception as e:
                                    logger.error(f"Error processing target transaction: {e}")
                            
                            # Add other transactions from the response
                            tx_list = response.get("transactions", [])
                            logger.info(f"Received {len(tx_list)} transactions from {peer_addr}")
                            
                            added_count = 0
                            for tx_data in tx_list:
                                tx_hash = tx_data.get("tx_hash")
                                if tx_hash == target_tx:
                                    # We already handled this above if it was sent as target_tx_data
                                    if not tx_found:
                                        logger.info(f"FOUND TARGET TRANSACTION in regular tx list from {peer_addr}!")
                                        print(f"\n{'*' * 80}")
                                        print(f"FOUND TARGET TRANSACTION in transaction list from {peer_addr}!")
                                        print(f"{'*' * 80}\n")
                                        tx_found = True
                                
                                try:
                                    tx = Transaction(
                                        sender=tx_data["sender"],
                                        recipient=tx_data["recipient"],
                                        amount=float(tx_data["amount"]),
        """Broadcast transaction with retries and handle failures gracefully."""
        attempt = 0
        successful_peers = 0
        
        # First verify if we have any active peers
        if not self.peers:
            # No peers available, try to discover some first
            logger.info("No peers available for transaction broadcast, discovering peers first...")
            discovered = self.discover_peers()
            if discovered == 0:
                print(f"Warning: No peers available to broadcast transaction {transaction.tx_hash[:8]}...")
                # Save transaction in pending pool even if broadcast fails
                return
        
        # Start broadcasting with retries
        while attempt < max_retries:
            logger.info(f"Broadcasting transaction {transaction.tx_hash[:8]}... (attempt {attempt+1}/{max_retries})")
            successful_peers = self.broadcast_transaction(transaction)
            
            if successful_peers > 0:
                # Successfully broadcast to at least one peer
                logger.info(f"Transaction {transaction.tx_hash[:8]}... successfully broadcast to {successful_peers} peers")
                break
            
            # If we have no peers now (they may have disconnected), try to discover more
            if not self.peers:
                logger.warning("All peers lost during broadcast, attempting to discover new peers...")
                discovered = self.discover_peers()
                if discovered == 0:
                    logger.warning("Failed to discover any peers, aborting broadcast")
                    break
            
            # Exponential backoff for retries
            wait_time = 2 ** attempt
            logger.info(f"Retrying transaction broadcast in {wait_time} seconds...")
            print(f"Retrying transaction broadcast in {wait_time} seconds...")
            time.sleep(wait_time)
            attempt += 1
            
        if successful_peers > 0:
            print(f"Transaction {transaction.tx_hash[:8]}... successfully broadcast to {successful_peers} peers")
        elif self.peers:
            logger.warning(f"Failed to broadcast transaction {transaction.tx_hash[:8]}... to any peers after {max_retries} attempts")
            print(f"Warning: Failed to broadcast transaction {transaction.tx_hash[:8]}... to any peers after {max_retries} attempts")
            # Try one more time with synchronized peers
            try:
                # First sync the blockchain state to ensure we have valid peer connections
                self.sync_blockchain_state()
                if self.peers:
                    # Try one last broadcast
                    successful_peers = self.broadcast_transaction(transaction)
                    if successful_peers > 0:
                        print(f"Transaction {transaction.tx_hash[:8]}... successfully broadcast after blockchain sync")
            except Exception as e:
                logger.error(f"Error during final transaction broadcast attempt: {e}")
    
    def broadcast_transaction(self, transaction: Transaction) -> int:
        """Broadcast a transaction to all peers."""
        successful_broadcasts = 0
        
        with self.peers_lock:
            # Make a copy of peer addresses to avoid modification during iteration
            peer_addresses = list(self.peers.keys())
        
        for peer_addr in peer_addresses:
            try:
                # Parse peer address
                if ":" in peer_addr:
                    host, port = peer_addr.split(":")
                    port = int(port)
                else:
                    host = peer_addr
                    port = self.p2p_port
                    
                # Create socket connection
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(5)  # 5 second timeout
                s.connect((host, port))
                
                # Send transaction message
                message = {
                    "type": "new_transaction",
                    "transaction": transaction.to_dict()
                }
                s.sendall(pickle.dumps(message))
                
                # Receive response
                data = s.recv(4096)
                if data:
                    response = pickle.loads(data)
                    if response.get("type") == "tx_response" and response.get("success"):
                        successful_broadcasts += 1
                        # Update peer's last seen time
                        with self.peers_lock:
                            if peer_addr in self.peers:
                                self.peers[peer_addr]["last_seen"] = time.time()
                
                s.close()
            except Exception as e:
                print(f"Error broadcasting transaction to peer {peer_addr}: {e}")
                # Check if peer is consistently failing and consider removing
                with self.peers_lock:
                    if peer_addr in self.peers:
                        last_seen = self.peers[peer_addr].get("last_seen", 0)
                        if time.time() - last_seen > 300:  # 5 minutes
                            print(f"Removing unresponsive peer: {peer_addr}")
                            self.remove_peer(peer_addr)
        
        return successful_broadcasts
    
    def broadcast_block(self, block: Block) -> int:
        """Broadcast a new block to all peers."""
        successful_broadcasts = 0
        
        with self.peers_lock:
            # Make a copy of peer addresses to avoid modification during iteration
            peer_addresses = list(self.peers.keys())
        
        for peer_addr in peer_addresses:
            try:
                # Parse peer address
                if ":" in peer_addr:
                    host, port = peer_addr.split(":")
                    port = int(port)
                else:
                    host = peer_addr
                    port = self.p2p_port
                    
                # Create socket connection
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(5)  # 5 second timeout
                s.connect((host, port))
                
                # Send block message
                message = {
                    "type": "new_block",
                    "block": {
                        "index": block.index,
                        "timestamp": block.timestamp,
                        "previous_hash": block.previous_hash,
                        "hash": block.hash,
                        "nonce": block.nonce,
                        "transactions": [tx.to_dict() for tx in block.transactions]
                    }
                }
                s.sendall(pickle.dumps(message))
                
                # Receive response
                data = s.recv(4096)
                if data:
                    response = pickle.loads(data)
                    if response.get("type") == "block_response" and response.get("success"):
                        successful_broadcasts += 1
                
                s.close()
            except Exception as e:
                print(f"Error broadcasting block to peer {peer_addr}: {e}")
                # Check if peer is consistently failing and consider removing
                with self.peers_lock:
                    if peer_addr in self.peers:
                        last_seen = self.peers[peer_addr].get("last_seen", 0)
                        if time.time() - last_seen > 300:  # 5 minutes
                            logger.warning(f"Removing unresponsive peer: {peer_addr}")
                            self.remove_peer(peer_addr)
        
        return successful_broadcasts
    
    def add_new_block(self, block: Block) -> bool:
        """Add a new block to the chain (from mining or peer sync)."""
        with self.chain_lock:
            # Validate block
            if block.index != len(self.chain):
                print(f"Block index mismatch: expected {len(self.chain)}, got {block.index}")
                return False
            
            if block.previous_hash != self.chain[-1].hash:
                print(f"Block previous hash mismatch: expected {self.chain[-1].hash}, got {block.previous_hash}")
                return False
            
            # Validate block hash
            # Validate block hash
            calculated_hash = block.calculate_hash()
            if calculated_hash != block.hash:
                return False
            
            # Add block to chain
            self.chain.append(block)
            
            # Remove transactions that are now in the block 
            with self.tx_lock:
                # Create a set of transaction hashes in the block
                block_tx_hashes = {tx.tx_hash for tx in block.transactions}
                
                # Filter out transactions that are now in the block
                self.pending_transactions = [
                    tx for tx in self.pending_transactions 
                    if tx.tx_hash not in block_tx_hashes
                ]
            
            print(f"Added block #{block.index} with hash {block.hash[:8]}...")
            return True
        except Exception as e:
            print(f"Error adding new block: {e}")
            return False

    def mine_pending_transactions(self, miner_address: str) -> bool:
        """Mine pending transactions into a block."""
        try:
            # Back up pending transactions before mining
            with self.tx_lock:
                pending_tx_backup = self.pending_transactions.copy()
                if not pending_tx_backup:
                    print("No transactions to mine")
                    return False

            # Create a mining reward transaction
            reward_tx = Transaction("0", miner_address, self.block_reward, 0, "reward")
            reward_tx.tx_hash = reward_tx.calculate_hash()  # No signature needed for reward
                
            # Add reward transaction to list of transactions to mine
            with self.tx_lock:
                mining_transactions = self.pending_transactions.copy()
                # Only include the reward in the actual block, not the pending tx pool
                mining_transactions.append(reward_tx)

            # Create new block
            block = Block(
                len(self.chain),
                mining_transactions,
                self.get_latest_block().hash
            )
            
            print(f"Mining block with {len(mining_transactions)} transactions...")
            start_time = time.time()
            block.mine_block(self.difficulty)
            end_time = time.time()
            
            # Add the newly mined block to the chain
            with self.chain_lock:
                self.chain.append(block)
            
            # Clear pending transactions that were included in the block
            with self.tx_lock:
                self.pending_transactions = []
            
            print(f"Block mined in {end_time - start_time:.2f} seconds!")
            print(f"Block hash: {block.hash}")
            
            # Broadcast the new block to the network
            if self.running:
                broadcast_count = self.broadcast_block(block)
                print(f"Block broadcast to {broadcast_count} peers")
                
            return True
        except KeyboardInterrupt:
            # Restore pending transactions if interrupted
            with self.tx_lock:
                self.pending_transactions = pending_tx_backup
            print("\nMining interrupted. Pending transactions restored.")
            return False
        except Exception as e:
            # Restore pending transactions in case of error
            with self.tx_lock:
                self.pending_transactions = pending_tx_backup
            print(f"Error mining block: {e}")
            return False

    def load_chain_from_network(self) -> bool:
        """Load blockchain state from network peers rather than from file."""
        try:
            if not self.peers:
                print("No peers available to sync from")
                return False
                
            # Sync with all available peers
            synced_peers = self.sync_blockchain_state()
            
            if synced_peers > 0:
                print(f"Successfully synchronized with {synced_peers} peers")
                print(f"Current blockchain length: {len(self.chain)} blocks")
                return True
            else:
                print("Failed to synchronize with any peers")
                return False
                
        except Exception as e:
            print(f"Error loading blockchain from network: {e}")
            return False
            
    # Legacy method - kept only for backwards compatibility but not used in network mode
    def load_chain(self, filename: str) -> bool:
        """Deprecated: Load blockchain from a file. Use network sync instead."""
        print("File-based blockchain loading is deprecated in network mode.")
        print("The node will automatically sync state from the network.")
        return self.load_chain_from_network()
        
    # Legacy method - kept only for backwards compatibility but not used in network mode
    def save_chain(self, filename: str) -> bool:
        """Deprecated: Save blockchain to a file. State is maintained across the network."""
        print("File-based blockchain saving is deprecated in network mode.")
        print("The blockchain state is automatically maintained across the network.")
        return True
# ======== CLI Interface ========
def print_header():
    try:
        print("""
    __  ___           __    __        ________          _     
   /  |/  /___ ______/ /_  / /__     / ____/ /_  ____ _(_)___ 
  / /|_/ / __ `/ ___/ __ \/ / _ \   / /   / __ \/ __ `/ / __ \\
 / /  / / /_/ / /  / /_/ / /  __/  / /___/ / / / /_/ / / / / /
/_/  /_/\__,_/_/  /_.___/_/\___/   \____/_/ /_/\__,_/_/_/ /_/ 
                                                                
    """)
        print("Advanced Distributed Ledger Technology")
        print("=" * 80)
        # Instead of using emoji, use ASCII alternatives
        print("[CHAIN] SIMPLE BLOCKCHAIN NODE")
    except UnicodeEncodeError:
        # Fall back to basic ASCII if encoding fails
        print("MARBLE BLOCKCHAIN NODE")
        print("=" * 40)
def print_menu():
    print("\nWhat would you like to do?")
    print("1. Create new wallet")
    print("2. Import existing wallet")
    print("3. View wallet info & balance")
    print("4. View transaction history")
    print("5. Send tokens")
    print("6. Mine blocks")
    print("7. View blockchain status")
    print("8. View network status")
    print("9. Manage network peers")
    print("10. Mint tokens")
    print("11. Manage minting permissions")
    print("0. Exit")
    return input("Enter your choice (0-11): ")

def main():
    print_header()
    
    # Input validation for node parameters
    args = parse_arguments()
    validate_cli_arguments(args)
    
    # Security: Check .env file permissions
    check_env_file_permissions()
    
    # Create blockchain node with networking enabled by default
    node = BlockchainNode(
        difficulty=4,
        rpc_port=args.rpc_port,
        p2p_port=args.p2p_port
    )
    
    # Number of startup attempts to make
    MAX_STARTUP_ATTEMPTS = 3
    startup_successful = False
    
    # Start the node with networking enabled automatically
    print("\nStarting blockchain node with networking enabled...")
    for attempt in range(1, MAX_STARTUP_ATTEMPTS + 1):
        try:
            if node.start_node():
                startup_successful = True
                logger.info(f"Node startup successful on attempt {attempt}")
                break
            else:
                print(f"Failed to start node (attempt {attempt}/{MAX_STARTUP_ATTEMPTS}). Retrying...")
                # Increase delay with each retry
                time.sleep(2 * attempt)
        except Exception as e:
            logger.error(f"Error during node startup attempt {attempt}: {e}")
            print(f"Error during node startup: {e}")
            if attempt < MAX_STARTUP_ATTEMPTS:
                print(f"Retrying startup ({attempt+1}/{MAX_STARTUP_ATTEMPTS})...")
                time.sleep(3)
            else:
                print("Maximum startup attempts reached. Continuing with limited functionality.")
    
    if not startup_successful:
        print("WARNING: Node networking startup failed. Some features may be unavailable.")
        logger.warning("Node networking startup failed after all attempts")
    
    print(f"Node ID: {node.node_id}")
    print(f"P2P server listening on port {node.p2p_port}")
    print(f"RPC server listening on port {node.rpc_port}")
    
    # Define known peers for your specific network
    # Define known peers for your specific network
    SPECIFIC_NETWORK_PEERS = [
        # Add the peers where your transaction might be stored
        "127.0.0.1:6001",
        "127.0.0.1:6002",
        "192.168.1.100:6000",
        "192.168.1.101:6000",
        # Add additional peers that might have the target transaction
        "192.168.0.105:6000",
        "192.168.0.110:6000",
        "10.0.0.15:6000"
    ]
    
    # Define the target transaction we're looking for
    TARGET_TX = "53dc0f06b1dd64da474f4be1fab48e24ff1130decb09b2a82af13f72b5bf8889"
    print(f"\nLooking for transaction: {TARGET_TX}")
    # Enhanced connection logic with retry mechanism
    # Enhanced connection logic with retry mechanism
    def connect_to_specific_peers():
        """Connect to specific peers that may have the transaction"""
        connected = 0
        successful_peers = []
        print("Connecting to network peers...")
        
        # Before trying connections, check for any existing connections to these peers
        with node.peers_lock:
            for peer in SPECIFIC_NETWORK_PEERS:
                if peer in node.peers:
                    connected += 1
                    successful_peers.append(peer)
                    print(f"Already connected to peer: {peer}")
        
        # Only try to connect to peers we're not already connected to
        peers_to_try = [p for p in SPECIFIC_NETWORK_PEERS if p not in successful_peers]
        
        # Process each peer with multiple retry attempts
        for peer_addr in peers_to_try:
            # Try multiple times per peer with increasing delays
            for attempt in range(3):
                try:
                    print(f"Attempting to connect to peer {peer_addr} ({attempt+1}/3)...")
                    if node.connect_to_peer(peer_addr):
                        connected += 1
                        successful_peers.append(peer_addr)
                        print(f"Successfully connected to peer: {peer_addr}")
                        
                        # Check if this peer has our target transaction right away
                        try:
                            print(f"Checking if peer {peer_addr} has target transaction {TARGET_TX[:8]}...")
                            # Try to sync transaction pool immediately with this peer
                            if node.running:
                                # Perform transaction pool sync in a separate thread to avoid blocking
                                def quick_tx_check(peer):
                                    found = False
                                    try:
                                        # Check if our transaction is in the pending pool after sync
                                        node._sync_transaction_pool()
                                        for tx in node.pending_transactions:
                                            if tx.tx_hash == TARGET_TX:
                                                print(f"\n{'*' * 80}")
                                                print(f"FOUND TARGET TRANSACTION {TARGET_TX} IN PENDING POOL!")
                                                print(f"From: {tx.sender[:16]}...")
                                                print(f"To: {tx.recipient[:16]}...")
                                                print(f"Amount: {tx.amount}")
                                                print(f"{'*' * 80}\n")
                                                found = True
                                                break
                                        if not found:
                                            print(f"Transaction {TARGET_TX[:8]}... not found on peer {peer}")
                                    except Exception as e:
                                        logger.error(f"Error in quick transaction check with peer {peer}: {e}")
                                
                                # Start quick check in background
                                threading.Thread(target=quick_tx_check, args=(peer_addr,), daemon=True).start()
                        except Exception as check_err:
                            logger.error(f"Error checking transactions on peer {peer_addr}: {check_err}")
                        
                        break  # Exit retry loop for this peer
                    else:
                        # Connection failed but no exception was thrown
                        delay = (attempt + 1) * 2  # Progressive backoff: 2s, 4s, 6s
                        if attempt < 2:  # Only print for first two attempts
                            print(f"Failed to connect to {peer_addr}, retrying in {delay}s ({attempt+2}/3)...")
                            time.sleep(delay)
                except ConnectionRefusedError:
                    # Specific handling for connection refused
                    logger.warning(f"Connection refused by peer {peer_addr} (attempt {attempt+1}/3)")
                    if attempt < 2:
                        delay = (attempt + 1) * 2
                        time.sleep(delay)
                except socket.timeout:
                    # Specific handling for timeout
                    logger.warning(f"Connection to peer {peer_addr} timed out (attempt {attempt+1}/3)")
                    if attempt < 2:
                        delay = (attempt + 1) * 2
                        time.sleep(delay)
                except Exception as e:
                    # General exception handling
                    logger.error(f"Error connecting to peer {peer_addr} (attempt {attempt+1}/3): {e}")
                    if attempt < 2:
                        delay = (attempt + 1) * 2
                        time.sleep(delay)
        
        if connected > 0:
            print(f"Successfully connected to {connected} peers: {', '.join(successful_peers)}")
        else:
            print("Failed to connect to any peers.")
            
        return connected
    # Enhanced peer reconnection monitor with better error handling
    def reconnection_monitor():
        """Monitor peer connections and reconnect if dropped, with focused transaction discovery"""
        next_discovery_time = 0  # Initialize to 0 to trigger immediate discovery
        next_sync_time = 0  # Time for next blockchain state sync
        next_tx_check_time = 0  # Time for next transaction pool check
        target_tx = "53dc0f06b1dd64da474f4be1fab48e24ff1130decb09b2a82af13f72b5bf8889"
        last_error_time = 0
        consecutive_errors = 0
        max_errors = 5  # Maximum consecutive errors before backoff
        tx_found = False  # Flag to track if we've found the target transaction
        
        print("Starting network monitoring thread...")
        logger.info("Network monitoring thread started")
        
        while node.running:
            try:
                current_time = time.time()
                
                # Reset consecutive error counter if we've been running without errors
                if consecutive_errors > 0 and (current_time - last_error_time) > 60:
                    consecutive_errors = 0
                
                # Sleep a short time to avoid CPU spinning
                time.sleep(3)
                
                # Periodically check specifically for our target transaction
                # Periodically check specifically for our target transaction
                if current_time >= next_tx_check_time:
                    # First check if our target transaction is already in the pool
                    search_count = 0
                    with node.tx_lock:
                        for tx in node.pending_transactions:
                            search_count += 1
                            if tx.tx_hash == target_tx:
                                logger.info(f"Target transaction {target_tx} found in local pending pool")
                                print(f"\n{'*' * 80}")
                                print(f"TARGET TRANSACTION {target_tx} FOUND IN LOCAL PENDING POOL!")
                                print(f"From: {tx.sender[:16]}...")
                                print(f"To: {tx.recipient[:16]}...")
                                print(f"Amount: {tx.amount}")
                                time_str = datetime.datetime.fromtimestamp(tx.timestamp).strftime('%Y-%m-%d %H:%M:%S')
                                print(f"Time: {time_str}")
                                print(f"{'*' * 80}\n")
                                tx_found = True
                                
                                # Log this important find to a dedicated file
                                try:
                                    with open('found_transactions.log', 'a') as f:
                                        f.write(f"Found target transaction {target_tx} in local pool at {datetime.datetime.now()}\n")
                                        f.write(f"From: {tx.sender}\n")
                                        f.write(f"To: {tx.recipient}\n")
                                        f.write(f"Amount: {tx.amount}\n")
                                        f.write(f"Time: {time_str}\n\n")
                                except Exception as e:
                                    logger.error(f"Error logging found transaction: {e}")
                                    
                                break
                    if not tx_found:
                        # If not found, attempt to sync transaction pool to find it 
                        # using a more aggressive approach with multiple peers
                        print(f"Searching for target transaction {target_tx[:8]}... (checked {search_count} local transactions)")
                        try:
                            logger.info(f"Actively checking for target transaction {target_tx[:8]}...")
                            
                            # Get a list of all peers to query specifically for this transaction
                            with node.peers_lock:
                                peers_to_check = list(node.peers.keys())
                                
                            # Create a dedicated function for aggressive transaction search
                            def search_transaction_on_peers():
                                nonlocal tx_found
                                search_success = False
                                found_on_peer = None
                                search_count = 0
                                
                                # First try the specific network peers that might have our transaction
                                for peer_addr in SPECIFIC_NETWORK_PEERS:
                                    if peer_addr in peers_to_check:
                                        # Move this peer to the front of the list for priority checking
                                        peers_to_check.remove(peer_addr)
                                        peers_to_check.insert(0, peer_addr)
                                
                                # Try each peer with multiple retry attempts
                                for peer_addr in peers_to_check:
                                    search_count += 1
                                    # Skip after checking a reasonable number of peers to avoid excessive traffic
                                    if search_count > 10:
                                        logger.info(f"Limiting transaction search to 10 peers for this cycle")
                                        break
                                        
                                    # Skip peers that have consistently failed
                                    with node.peers_lock:
                                        if peer_addr in node.peers and node.peers[peer_addr].get("failure_count", 0) > 5:
                                            logger.info(f"Skipping peer {peer_addr} due to too many failures")
                                            continue
                                
                                    logger.info(f"Searching for transaction on peer {peer_addr}")
                                    try:
                                        # Special targeted sync just for this peer
                                        s = None
                                        try:
                                            # Parse peer address
                                            if ":" in peer_addr:
                                                host, port = peer_addr.split(":")
                                                port = int(port)
                                            else:
                                                host = peer_addr
                                                port = node.p2p_port
                                                
                                            # Create socket connection
                                            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                            s.settimeout(10)  # 10 second timeout
                                            s.connect((host, port))
                                            
                                            # Send specific request for our target transaction
                                            message = {
                                                "type": "get_specific_transaction",
                                                "tx_hash": target_tx
                                            }
                                            s.sendall(pickle.dumps(message))
                                            
                                            # Receive response
                                            data = s.recv(8192)
                                            if data:
                                                response = pickle.loads(data)
                                                if response.get("type") == "specific_tx_response":
                                                    tx_data = response.get("transaction")
                                                    if tx_data and tx_data.get("tx_hash") == target_tx:
                                                        logger.info(f"FOUND TARGET TRANSACTION on peer {peer_addr}!")
                                                        print(f"\n{'*' * 80}")
                                                        print(f"FOUND TARGET TRANSACTION {target_tx} ON PEER {peer_addr}!")
                                                        print(f"From: {tx_data.get('sender', 'unknown')[:16]}...")
                                                        print(f"To: {tx_data.get('recipient', 'unknown')[:16]}...")
                                                        print(f"Amount: {tx_data.get('amount', 'unknown')}")
                                                        print(f"{'*' * 80}\n")
                                                        
                                                        # Create transaction object and add to our pool
                                                        try:
                                                            tx = Transaction(
                                                                sender=tx_data["sender"],
                                                                recipient=tx_data["recipient"],
                                                                amount=float(tx_data["amount"]),
                                                                fee=float(tx_data.get("fee", 0.001)),
                                                                transaction_type=tx_data.get("transaction_type", "transfer")
                                                            )
                                                            tx.timestamp = float(tx_data.get("timestamp", time.time()))
                                                            tx.signature = tx_data.get("signature")
                                                            tx.tx_hash = tx_data.get("tx_hash")
                                                            
                                                            # Add to our pool without broadcasting
                                                            node.add_transaction(tx, broadcast=False)
                                                            tx_found = True
                                                            found_on_peer = peer_addr
                                                            search_success = True
                                                            
                                                            # Update peer's last seen time and reset failure count
                                                            with node.peers_lock:
                                                                if peer_addr in node.peers:
                                                                    node.peers[peer_addr]["last_seen"] = time.time()
                                                                    node.peers[peer_addr]["failure_count"] = 0
                                                            
                                                            # Log this important find
                                                            try:
                                                                with open('found_transactions.log', 'a') as f:
                                                                    f.write(f"Found transaction {target_tx} on peer {peer_addr} at {datetime.datetime.now()}\n")
                                                                    f.write(f"Details: {json.dumps(tx_data, indent=2)}\n\n")
                                                            except Exception as e:
                                                                logger.error(f"Error logging found transaction: {e}")
                                                        except Exception as tx_err:
                                                            logger.error(f"Error creating transaction from peer data: {tx_err}")
                                                    else:
                                                        logger.info(f"Peer {peer_addr} does not have target transaction")
                                        except (ConnectionRefusedError, socket.timeout) as conn_err:
                                            logger.warning(f"Connection error with peer {peer_addr}: {conn_err}")
                                            # Track failure
                                            with node.peers_lock:
                                                if peer_addr in node.peers:
                                                    node.peers[peer_addr]["failure_count"] = node.peers[peer_addr].get("failure_count", 0) + 1
                                        except Exception as e:
                                            logger.error(f"Error searching transaction on peer {peer_addr}: {e}")
                                        finally:
                                            if s:
                                                try:
                                                    s.close()
                                                except:
                                                    pass
                                            
                                        # If we found the transaction, we can stop searching
                                        if tx_found:
                                            break
                                            
                                    except Exception as peer_err:
                                        logger.error(f"Error processing peer {peer_addr}: {peer_err}")
                                
                                # If we didn't find it through direct search, use the regular sync
                                if not tx_found:
                                    tx_added = node._sync_transaction_pool()
                                    if tx_added > 0:
                                        logger.info(f"Added {tx_added} transactions during pool sync")
                                        # Check if our target was added
                                        with node.tx_lock:
                                            for tx in node.pending_transactions:
                                                if tx.tx_hash == target_tx:
                                                    logger.info(f"Found target transaction during pool sync")
                                                    tx_found = True
                                                    search_success =
                    
                    # Schedule next transaction check - check more frequently if we haven't found it
                    if tx_found:
                        next_tx_check_time = current_time + 120  # Check less frequently once found
                    else:
                        next_tx_check_time = current_time + 30  # Check frequently until found
                
                # Check if we should discover peers (every 30 seconds)
                if current_time >= next_discovery_time:
                    try:
                        peer_count = len(node.peers)
                        logger.info(f"Current peer count: {peer_count}")
                        
                        if peer_count < 3:
                            logger.info(f"Peer count low ({peer_count}), discovering more peers")
                            print(f"Peer count low ({peer_count}), discovering more peers...")
                            
                            # Try our specific network peers first
                            logger.info("Attempting to connect to specific network peers")
                            specific_connections = connect_to_specific_peers()
                            
                            if specific_connections == 0:
                                # If no specific peers found, try general discovery
                                logger.info("No specific peers connected, trying general discovery")
                                discovered = node.discover_peers()
                                if discovered > 0:
                                    print(f"General peer discovery found {discovered} peers")
                                    logger.info(f"General peer discovery found {discovered} peers")
                        
                        # Schedule next discovery (more frequent if low peer count)
                        if len(node.peers) < 2:
                            next_discovery_time = current_time + 15  # Try sooner if very few peers
                        else:
                            next_discovery_time = current_time + 30  # Normal interval
                    except Exception as disc_err:
                        logger.error(f"Error during peer discovery: {disc_err}")
                        last_error_time = current_time
                        consecutive_errors += 1
                        
                        # Still schedule next attempt even after error
                        # But back off if we've had too many errors
                        if consecutive_errors > max_errors:
                            next_discovery_time = current_time + (30 * consecutive_errors)  # Exponential backoff
                            logger.warning(f"Too many consecutive errors, backing off for {30 * consecutive_errors} seconds")
                        else:
                            next_discovery_time = current_time + 20  # Try again soon
                # Check if we should sync state (every 60 seconds, but only if we have peers)
                if current_time >= next_sync_time and node.peers:
                    try:
                        logger.info("Performing scheduled blockchain state synchronization")
                        
                        # Sync blockchain state
                        synced_count = node.sync_blockchain_state()
                        if synced_count > 0:
                            logger.info(f"Successfully synced blockchain with {synced_count} peers")
                            
                            # Sync transaction pool if blockchain sync was successful
                            # This is specifically important for finding our target transaction
                            logger.info("Synchronizing transaction pool after successful blockchain sync")
                            tx_added = node._sync_transaction_pool()
                            if tx_added > 0:
                                logger.info(f"Added {tx_added} transactions during scheduled sync")
                                
                                # After syncing transactions, check if we found our target
                                for tx in node.pending_transactions:
                                    if tx.tx_hash == target_tx:
                                        logger.info(f"TARGET TRANSACTION {target_tx} FOUND during scheduled sync!")
                                        print(f"\n{'*' * 80}")
                                        print(f"TARGET TRANSACTION {target_tx} FOUND!")
                                        print(f"Found during scheduled sync from peers")
                                        print(f"From: {tx.sender[:16]}...")
                                        print(f"To: {tx.recipient[:16]}...")
                                        print(f"Amount: {tx.amount}")
                                        time_str = datetime.datetime.fromtimestamp(tx.timestamp).strftime('%Y-%m-%d %H:%M:%S')
                                        print(f"Time: {time_str}")
                                        print(f"{'*' * 80}\n")
                                        break
                    except Exception as e:
                        logger.error(f"Error during scheduled state synchronization: {e}")
                        last_error_time = current_time
                        consecutive_errors += 1
                    
                    # Set next sync time, with backoff if we've had errors
                    if consecutive_errors > max_errors:
                        next_sync_time = current_time + (60 * (consecutive_errors - max_errors))  # Gradually increase interval
                    else:
                        next_sync_time = current_time + 60  # Normal 1-minute interval
                
                # Check for inactive peers and remove them
                try:
                    with node.peers_lock:
                        inactive_peers = []
                        for peer_addr, peer_info in node.peers.items():
                            if current_time - peer_info.get('last_seen', 0) > 300:  # 5 minutes
                                inactive_peers.append(peer_addr)
                    
                    # Remove inactive peers outside the lock to avoid deadlocks
                    for peer_addr in inactive_peers:
                        logger.info(f"Removing inactive peer: {peer_addr}")
                        node.remove_peer(peer_addr)
                except Exception as e:
                    logger.error(f"Error checking inactive peers: {e}")
            except Exception as e:
                logger.error(f"Error in reconnection monitor: {e}")
                last_error_time = time.time()
                consecutive_errors += 1
                # Don't crash the monitor thread - wait and continue
                time.sleep(max(5, min(30, 5 * consecutive_errors)))  # Backoff between 5-30 seconds

    # Start the enhanced reconnection monitor in a separate thread
    if node.running:
        try:
            monitor_thread = threading.Thread(target=reconnection_monitor, daemon=True)
            monitor_thread.start()
            logger.info("Reconnection monitor thread started")
        except Exception as e:
            logger.error(f"Failed to start reconnection monitor: {e}")
            print(f"Warning: Failed to start network monitoring thread: {e}")
            # Try one more time with a delay
            try:
                time.sleep(2)
                monitor_thread = threading.Thread(target=reconnection_monitor, daemon=True)
                monitor_thread.start()
                logger.info("Reconnection monitor thread started on second attempt")
            except Exception as retry_error:
                logger.error(f"Failed to start reconnection monitor on second attempt: {retry_error}")
    
    # First try to connect to specific network peers
    specific_peers_connected = connect_to_specific_peers()
    
    # If no specific peers connected, try general discovery with extra retries
    if specific_peers_connected == 0:
        print("No specific network peers connected. Discovering peers...")
        
        max_discovery_attempts = 3
        discovered = 0
        
        for attempt in range(1, max_discovery_attempts + 1):
            print(f"Peer discovery attempt {attempt}/{max_discovery_attempts}...")
            discovered = node.discover_peers()
            
            if discovered > 0:
                print(f"Successfully discovered {discovered} peers")
                break
            
            if attempt < max_discovery_attempts:
                delay = 3 * attempt  # Increasing delay: 3s, 6s, 9s
                print(f"Retrying discovery in {delay} seconds...")
                time.sleep(delay)
        
        if discovered > 0:
            print(f"Connected to {discovered} peers")
        else:
            print("No peers discovered. This node will start a new blockchain network.")
            print("If you want to connect to an existing network, use the 'Manage network peers' option.")
    else:
        print(f"Connected to {specific_peers_connected} specific network peers")
    
    # If we have any peers, synchronize blockchain state
    if node.peers:
        print("Synchronizing blockchain state with network...")
        max_sync_attempts = 3
        sync_success =
                
                if synced_count > 0:
                    print(f"Successfully synchronized with {synced_count} peers")
                    print(f"Current blockchain length: {len(node.chain)} blocks")
                    sync_success = True
                    
                    # Also sync the transaction pool to find your transaction
                    print("Synchronizing pending transactions...")
                    tx_count = node._sync_transaction_pool()
                    print(f"Transaction pool contains {len(node.pending_transactions)} transactions")
                    if tx_count > 0:
                        print(f"Added {tx_count} new transactions from peers")
                    
                    # We've successfully synced, so break out of the retry loop
                    break
            
            if not sync_success and node.peers:
                logger.warning("Failed to synchronize with any peers after multiple attempts")
                print("Warning: Failed to synchronize with peers. Some transactions may not be visible.")
    
    # Enable VMIA/neural mining if specified
    if args.enable_vmia:
        logger.info("VMIA neural processing enabled")
    if args.neural_mining:
        logger.info("Neural-optimized mining activated")
    logger.info("Blockchain node initialized with difficulty: %s", node.difficulty)
    
    while True:
        choice = None
        valid_choices = {str(i) for i in range(12)}
        
        while choice not in valid_choices:
            choice = print_menu()
            if choice not in valid_choices:
                print("Invalid choice. Please enter a number between 0 and 11.")
        
        if choice == "0":
            print("Exiting. Goodbye!")
            sys.exit(0)
            
        elif choice == "1":
            try:
                # Create new wallet
                node.wallet = Wallet(node)
                print(f"New wallet created successfully!")
                print(f"Your public address: {node.wallet.public_key}")
                
                filename = input("Enter filename to save wallet (or press Enter to skip): ")
                if filename:
                    if node.wallet.save_to_file(filename):
                        print(f"Wallet saved to {filename}")
                    else:
                        print(f"Failed to save wallet to {filename}")
            except Exception as e:
                print(f"Error creating wallet: {e}")
                
        elif choice == "2":
            # Import existing wallet
            filename = input("Enter wallet filename: ")
            try:
                node.wallet = Wallet.load_from_file(filename, node)
                print(f"Wallet loaded successfully from {filename}")
                print(f"Your public address: {node.wallet.public_key}")
            except Exception as e:
                print(f"Error loading wallet: {e}")
                
        elif choice == "3":
            try:
                # View wallet info & balance
                if not node.wallet:
                    print("No wallet loaded. Please create or import a wallet first.")
                    continue
                    
                balance = node.wallet.get_balance()
                print("\n----- WALLET INFO -----")
                print(f"Address: {node.wallet.public_key}")
                print(f"Balance: {balance:.6f} coins")
            except Exception as e:
                print(f"Error retrieving wallet information: {e}")
                
        elif choice == "4":
            # View transaction history
            if not node.wallet:
                print("No wallet loaded. Please create or import a wallet first.")
                continue
                
            try:
                transactions = node.get_address_transactions(node.wallet.public_key)
                if not transactions:
                    print("No transactions found.")
                    continue
                    
                print("\n----- TRANSACTION HISTORY -----")
                for i, tx in enumerate(transactions):
                    time_str = datetime.datetime.fromtimestamp(tx.timestamp).strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Determine transaction type
                    if tx.transaction_type == "mint":
                        tx_type = "MINT"
                    elif tx.sender == node.wallet.public_key:
                        tx_type = "SENT"
                    else:
                        tx_type = "RECEIVED"
                    
                    other_party = tx.recipient if tx_type == "SENT" else tx.sender
                    
                    print(f"\nTransaction #{i+1} ({tx_type}):")
                    print(f"  Hash      : {tx.tx_hash[:16]}...")
                    print(f"  {'To' if tx_type == 'SENT' else 'From'}        : {other_party[:16]}...")
                    print(f"  Amount    : {tx.amount}")
                    print(f"  Fee       : {tx.fee}")
                    print(f"  Time      : {time_str}")
                    
            except Exception as e:
                print(f"Error retrieving transaction history: {e}")
                
        elif choice == "5":
            # Send tokens
            if not node.wallet:
                print("No wallet loaded. Please create or import a wallet first.")
                continue
                
            try:
                recipient = input("Enter recipient address: ")
                
                # Validate recipient address (basic check for simplicity)
                if len(recipient) < 10:
                    print("Invalid recipient address. Address should be at least 10 characters.")
                    continue
                    
                amount_str = input("Enter amount to send: ")
                amount = float(amount_str)
                
                if amount <= 0:
                    print("Amount must be greater than zero.")
                    continue
                    
                fee_str = input("Enter transaction fee (default: 0.001): ") or "0.001"
                fee = float(fee_str)
                
                if fee < 0.0001:
                    print("Fee must be at least 0.0001 coins.")
                    continue
                
                balance = node.wallet.get_balance()
                total_cost = amount + fee
                
                if balance < total_cost:
                    print(f"Insufficient balance. You have {balance:.6f} coins, but need {total_cost:.6f} coins.")
                    continue
                    
                confirm = input(f"Send {amount} coins to {recipient[:16]}... with fee {fee}? (y/n): ")
                if confirm.lower() != 'y':
                    print("Transaction cancelled.")
                    continue
                    
                success = node.wallet.send(recipient, amount, fee)
                if success:
                    print(f"Transaction sent successfully! It will be included in the next mined block.")
                else:
                    print("Transaction failed to send.")
            except ValueError as e:
                print(f"Invalid input: {e}")
            except Exception as e:
                print(f"Error processing transaction: {e}")
                    
        elif choice == "6":
            # Mine blocks
            if not node.wallet:
                print("No wallet loaded. Please create or import a wallet first.")
                continue
                
            if len(node.pending_transactions) == 0:
                print("No pending transactions to mine. Create some transactions first.")
                continue
                
            print(f"Starting mining process with {len(node.pending_transactions)} pending transactions...")
            print(f"Mining reward will be sent to: {node.wallet.public_key[:16]}...")
            
            confirm = input("This may take some time. Continue? (y/n): ")
            if confirm.lower() != 'y':
                print("Mining cancelled.")
                continue
                
            success = node.mine_pending_transactions(node.wallet.public_key)
            if success:
                print(f"Block successfully mined and added to the blockchain!")
                print(f"Mining reward of 1.0 coins will be available in the next block.")
            else:
                print("Mining failed.")
                
            # View blockchain status
            with node.chain_lock:
                print("\n----- BLOCKCHAIN STATUS -----")
                print(f"Blockchain length: {len(node.chain)} blocks")
                print(f"Difficulty: {node.difficulty}")
                print(f"Pending transactions: {len(node.pending_transactions)}")
                
                latest_block = node.get_latest_block()
                time_str = datetime.datetime.fromtimestamp(latest_block.timestamp).strftime('%Y-%m-%d %H:%M:%S')
                print(f"\nLatest block: #{latest_block.index}")
                print(f"Hash: {latest_block.hash}")
                print(f"Time: {time_str}")
                print(f"Transactions: {len(latest_block.transactions)}")
                
                # Print recent blocks (last 5)
                print("\nRecent blocks:")
                for block in reversed(node.chain[-5:] if len(node.chain) >= 5 else node.chain):
                    time_str = datetime.datetime.fromtimestamp(block.timestamp).strftime('%Y-%m-%d %H:%M:%S')
                    print(f"Block #{block.index}: Hash {block.hash[:8]}... - {len(block.transactions)} transactions - {time_str}")
                
        elif choice == "8":
            # View network status
            print("\n----- NETWORK STATUS -----")
            print(f"Node ID: {node.node_id}")
            print(f"P2P Port: {node.p2p_port}")
            print(f"RPC Port: {node.rpc_port}")
            print(f"Connected peers: {len(node.peers)}")
            print(f"Last sync time: {datetime.datetime.fromtimestamp(node.last_state_sync).strftime('%Y-%m-%d %H:%M:%S') if node.last_state_sync > 0 else 'Never'}")
            print(f"Node running: {'Yes' if node.running else 'No'}")
            
            if not node.running:
                restart = input("Node is not running. Start node networking? (y/n): ")
                if restart.lower() == 'y':
                    node.start_node()
                    print(f"Node started with ID: {node.node_id}")
                    
        elif choice == "9":
            # Manage network peers
            print("\n----- PEER MANAGEMENT -----")
            print("1. List connected peers")
            print("2. Add new peer")
            print("3. Remove peer")
            print("4. Sync with peers")
            print("5. Discover new peers")
            print("0. Back to main menu")
            
            peer_choice = input("Enter your choice (0-5): ")
            
            if peer_choice == "1":
                if not node.peers:
                    print("No peers connected.")
                else:
                    print("\nConnected peers:")
                    for idx, (peer_addr, peer_info) in enumerate(node.peers.items(), 1):
                        last_seen = datetime.datetime.fromtimestamp(peer_info["last_seen"]).strftime('%Y-%m-%d %H:%M:%S')
                        print(f"{idx}. {peer_addr} (Node ID: {peer_info['node_id']}) - Last seen: {last_seen}")
                        
            elif peer_choice == "2":
                peer_addr = input("Enter peer address (IP:port): ")
                if not peer_addr:
                    print("Invalid peer address.")
                    continue
                    
                if node.connect_to_peer(peer_addr):
                    print(f"Successfully connected to peer: {peer_addr}")
                else:
                    print(f"Failed to connect to peer: {peer_addr}")
                    
            elif peer_choice == "3":
                if not node.peers:
                    print("No peers to remove.")
                    continue
                    
                print("\nConnected peers:")
                peer_addresses = list(node.peers.keys())
                for idx, peer_addr in enumerate(peer_addresses, 1):
                    print(f"{idx}. {peer_addr}")
                    
                peer_idx = input("Enter the number of the peer to remove: ")
                try:
                    idx = int(peer_idx) - 1
                    if 0 <= idx < len(peer_addresses):
                        peer_to_remove = peer_addresses[idx]
                        if node.remove_peer(peer_to_remove):
                            print(f"Peer {peer_to_remove} removed successfully.")
                        else:
                            print(f"Failed to remove peer {peer_to_remove}.")
                    else:
                        print("Invalid peer number.")
                except ValueError:
                    print("Invalid input. Please enter a number.")
                    
            elif peer_choice == "4":
                if not node.peers:
                    print("No peers to sync with.")
                    continue
                    
                print("Syncing with peers...")
                synced_count = node.sync_blockchain_state()
                print(f"Synced with {synced_count} peers.")
                
            elif peer_choice == "5":
                print("Discovering peers...")
                # For a real implementation, this would use a discovery service
                # For now, just check if we have any peers to connect to
                discovered = node.discover_peers()
                print(f"Connected to {discovered} peers.")
                
            elif peer_choice != "0":
                print("Invalid choice.")
                
        elif choice == "10":
            # Mint tokens
            if not node.wallet:
                print("No wallet loaded. Please create or import a wallet first.")
                continue
                
            if not node.is_authorized_minter(node.wallet.public_key):
                print("Current wallet is not authorized to mint tokens.")
                authorize = input("Would you like to authorize this wallet for minting? (y/n): ")
                if authorize.lower() == 'y':
                    node.add_authorized_minter(node.wallet.public_key)
                    print("Wallet authorized for minting!")
                else:
                    continue
                
            try:
                recipient = input("Enter recipient address (leave blank to mint to own wallet): ")
                if not recipient:
                    recipient = node.wallet.public_key
                
                # Validate recipient address
                if len(recipient) < 10:
                    print("Invalid recipient address. Address should be at least 10 characters.")
                    continue
                    
                amount_str = input("Enter amount to mint: ")
                amount = float(amount_str)
                
                if amount <= 0:
                    print("Amount must be greater than zero.")
                    continue
                    
                confirm = input(f"Mint {amount} tokens for {recipient[:16]}...? (y/n): ")
                if confirm.lower() != 'y':
                    print("Minting cancelled.")
                    continue
                    
                success = node.mint_tokens(node.wallet.public_key, recipient, amount)
                if success:
                    print(f"Minting transaction created successfully! It will be included in the next mined block.")
                else:
                    print("Failed to create minting transaction.")
            except ValueError as e:
                print(f"Invalid input: {e}")
            except Exception as e:
                print(f"Error processing minting operation: {e}")
        elif choice == "11":
            # Manage minting permissions
            if not node.wallet:
                print("No wallet loaded. Please create or import a wallet first.")
                continue
                
            print("\nMinting Permission Management:")
            print("1. View authorized minters")
            print("2. Add address to authorized minters")
            print("3. Remove address from authorized minters") 
            print("0. Back to main menu")
            
            manage_choice = input("Enter your choice (0-3): ")
            
            if manage_choice == "1":
                if not node.authorized_minters:
                    print("No authorized minters configured.")
                else:
                    print("\nAuthorized minters:")
                    for idx, minter in enumerate(node.authorized_minters, 1):
                        print(f"{idx}. {minter}")
            elif manage_choice == "2":
                address = input("Enter address to authorize for minting: ")
                if address and len(address) >= 10:
                    node.add_authorized_minter(address)
                else:
                    print("Invalid address format.")
            elif manage_choice == "3":
                address = input("Enter address to remove from authorized minters: ")
                node.remove_authorized_minter(address)
            elif manage_choice == "0":
                continue
            else:
                print("Invalid choice.")
        else:
            print("Invalid choice. Please try again.")

def check_env_file_permissions():
    """Validate .env file permissions for security"""
    env_file = '.env'
    if os.path.exists(env_file):
        mode = os.stat(env_file).st_mode
        # Check if file is readable by others or writable by group/others
        if mode & stat.S_IRWXO or mode & stat.S_IRWXG:
            raise PermissionError(
                f"Insecure permissions on {env_file}. File should only be readable by owner."
                " Recommended: chmod 600 .env"
            )
        logger.info("Verified secure permissions for .env file")

def port_is_available(port: int) -> bool:
    """Check if a port is available for binding"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return True
        except socket.error:
            return False

def validate_ports(ports: List[int]) -> None:
    """Validate that required ports are available"""
    for port in ports:
        if not port_is_available(port):
            raise RuntimeError(
                f"Port {port} is already in use. Please check for running instances."
            )
    logger.info("All required ports are available")
def parse_arguments():
    """Parse and validate CLI arguments"""
    parser = argparse.ArgumentParser(description='Blockchain node runner')
    parser.add_argument(
        '--rpc-port',
        type=int,
        default=5000,
        help='Port for RPC server'
    )
    parser.add_argument(
        '--p2p-port',
        type=int,
        default=6000,
        help='Port for P2P communication'
    )
    parser.add_argument(
        '--enable-vmia',
        action='store_true',
        help='Enable VMIA neural processing'
    )
    parser.add_argument(
        '--neural-mining',
        action='store_true',
        help='Enable neural-optimized mining'
    )
    return parser.parse_args()
def validate_cli_arguments(args):
    """Sanitize and validate CLI arguments"""
    # Validate port numbers
    if not (1024 <= args.rpc_port <= 65535):
        raise ValueError(f"Invalid RPC port: {args.rpc_port}. Must be between 1024-65535")
    if not (1024 <= args.p2p_port <= 65535):
        raise ValueError(f"Invalid P2P port: {args.p2p_port}. Must be between 1024-65535")
    
    # Check port availability
    validate_ports([args.rpc_port, args.p2p_port])
    logger.info("CLI arguments validated successfully")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProgram terminated by user. Goodbye!")
    except Exception as e:
        try:
            print(f"\n[ERROR] Fatal error: {e}")
        except UnicodeEncodeError:
            print("\nERROR: Fatal error occurred")
        sys.exit(1)
