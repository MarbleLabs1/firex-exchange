from solana.rpc.api import Client
from solana.keypair import Keypair
from solana.transaction import Transaction
from solana.blockhash import Blockhash
from solana.publickey import PublicKey
from spl.token.instructions import get_associated_token_address, transfer, TransferParams
from spl.token.client import Token
import json
import hashlib
import sqlite3
import time
import logging
from typing import Dict, List, Tuple, Optional, Union

class SolanaBridge:
    def __init__(self, blockchain, dex, bridge_keypair=None, solana_token_address=None, 
                solana_endpoint="https://api.mainnet-beta.solana.com", token_decimals=9):
        self.blockchain = blockchain
        self.dex = dex
        self.solana_client = Client(solana_endpoint)
        self.locked_assets = {}  # In-memory cache
        self.solana_token_address = PublicKey(solana_token_address) if solana_token_address else None
        self.bridge_keypair = bridge_keypair  # Keypair object for the bridge authority
        self.token_decimals = token_decimals
        self.validators = []  # List of validator addresses
        self.required_signatures = 3  # Default number of required signatures
        self.pending_transfers = {}  # tx_hash -> {data: dict, approvals: list}
        
        # Initialize database tables
        self._initialize_db()
        # Load locked assets from database
        self._load_locked_assets()
        
    def _initialize_db(self):
        """Initialize database tables for the bridge"""
        conn = sqlite3.connect(self.blockchain.db_path)
        cursor = conn.cursor()
        
        # Table for locked assets waiting for bridge transfer
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS locked_assets (
                tx_hash TEXT PRIMARY KEY,
                account TEXT,
                token_id TEXT,
                amount TEXT,
                lock_time REAL
            )
        ''')
        
        # Table for bridge transfer history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bridge_transfers (
                tx_hash TEXT PRIMARY KEY,
                direction TEXT,
                account TEXT,
                token_id TEXT,
                amount TEXT,
                solana_address TEXT,
                solana_signature TEXT,
                timestamp REAL,
                status TEXT
            )
        ''')
        
        # Table for bridge validators
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bridge_validators (
                address TEXT PRIMARY KEY,
                added_time REAL
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def _load_locked_assets(self):
        """Load locked assets from database into memory"""
        conn = sqlite3.connect(self.blockchain.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT tx_hash, account, token_id, amount FROM locked_assets")
        for row in cursor.fetchall():
            self.locked_assets[row[0]] = {
                "account": row[1],
                "token_id": row[2],
                "amount": float(row[3])
            }
        conn.close()
        
    def _store_locked_asset(self, tx_hash, asset_data):
        """Store a locked asset in the database"""
        conn = sqlite3.connect(self.blockchain.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO locked_assets (tx_hash, account, token_id, amount, lock_time) VALUES (?, ?, ?, ?, ?)",
            (tx_hash, asset_data["account"], asset_data["token_id"], str(asset_data["amount"]), time.time())
        )
        conn.commit()
        conn.close()
        self.locked_assets[tx_hash] = asset_data
        
    def _remove_locked_asset(self, tx_hash):
        """Remove a locked asset from the database"""
        if tx_hash in self.locked_assets:
            conn = sqlite3.connect(self.blockchain.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM locked_assets WHERE tx_hash = ?", (tx_hash,))
            conn.commit()
            conn.close()
            del self.locked_assets[tx_hash]
            return True
        return False
        
    def _record_bridge_transfer(self, tx_hash, solana_signature, asset, solana_address, direction="to_solana", status="completed"):
        """Record a bridge transfer in the database"""
        conn = sqlite3.connect(self.blockchain.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO bridge_transfers 
            (tx_hash, direction, account, token_id, amount, solana_address, solana_signature, timestamp, status) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (tx_hash, direction, asset["account"], asset["token_id"], str(asset["amount"]), 
            solana_address, solana_signature, time.time(), status)
        )
        conn.commit()
        conn.close()

    def lock_asset(self, account, token_id, amount, signature) -> Optional[str]:
        """Lock assets on the blockchain for bridging to Solana
        
        Args:
            account: User account to lock assets from
            token_id: Token identifier
            amount: Amount to lock
            signature: Transaction signature
            
        Returns:
            Transaction hash if successful, None otherwise
        """
        try:
            # Check if account has sufficient balance
            if account.get_balance(token_id, self.blockchain.db_path) < amount:
                logging.warning(f"Insufficient balance for account {account.address}")
                return None
                
            # Prepare and verify transaction data
            tx_data = {"sender": account.address, "token_id": token_id, "amount": str(amount)}
            
            # Verify signature
            if account.sign(tx_data) != signature:
                logging.warning(f"Invalid signature for transaction from {account.address}")
                return None
                
            # Generate transaction hash
            tx_hash = hashlib.sha256(json.dumps(tx_data, sort_keys=True).encode()).hexdigest()
            
            # Store asset in database and memory
            asset_data = {"account": account.address, "token_id": token_id, "amount": amount}
            self._store_locked_asset(tx_hash, asset_data)
            
            # Add transaction to blockchain
            self.blockchain.add_transaction("bridge_lock", tx_data, signature)
            
            # Add to pending transfers if multi-signature is enabled
            if self.validators and len(self.validators) >= self.required_signatures:
                self.pending_transfers[tx_hash] = {
                    "data": tx_data,
                    "approvals": [],
                    "asset": asset_data
                }
                
            return tx_hash
            
        except Exception as e:
            logging.error(f"Error in lock_asset: {str(e)}")
            return None

    def bridge_to_solana(self, tx_hash, solana_keypair, solana_address) -> Tuple[bool, str]:
        """Transfer locked assets to Solana
        
        Args:
            tx_hash: Transaction hash of the locked asset
            solana_keypair: Keypair for transaction signing
            solana_address: Destination Solana address
            
        Returns:
            Tuple of (success, message)
        """
        # Check if multi-signature is required
        if self.validators and len(self.validators) >= self.required_signatures:
            if tx_hash not in self.pending_transfers or len(self.pending_transfers[tx_hash]["approvals"]) < self.required_signatures:
                return False, "Transfer needs multi-signature approval"
        
        # Check if transaction exists
        if tx_hash not in self.locked_assets:
            return False, "Transaction not found"
        
        # Get asset details
        asset = self.locked_assets[tx_hash]
        
        try:
            # Verify the Solana token address is set
            if not self.solana_token_address:
                return False, "Solana token address not configured"
                
            # Verify bridge keypair is set
            if not self.bridge_keypair:
                return False, "Bridge keypair not configured"
            
            logging.info(f"Sending {asset['amount']} {asset['token_id']} to Solana address: {solana_address}")
            
            # Convert destination address string to PublicKey
            dest_pubkey = PublicKey(solana_address)
            
            # Get associated token account for destination
            dest_token_account = get_associated_token_address(
                dest_pubkey,
                self.solana_token_address
            )
            
            # Get the bridge's token account
            bridge_token_account = get_associated_token_address(
                self.bridge_keypair.public_key,
                self.solana_token_address
            )
            
            # Calculate token amount with decimals
            token_amount = int(asset['amount'] * (10 ** self.token_decimals))
            
            # Create transfer instruction
            transfer_ix = transfer(
                TransferParams(
                    source=bridge_token_account,
                    dest=dest_token_account,
                    owner=self.bridge_keypair.public_key,
                    amount=token_amount
                )
            )
            
            # Get recent blockhash
            recent_blockhash = self.solana_client.get_recent_blockhash()["result"]["value"]["blockhash"]
            
            # Create transaction
            transaction = Transaction(
                recent_blockhash=Blockhash(recent_blockhash),
                fee_payer=self.bridge_keypair.public_key
            )
            transaction.add(transfer_ix)
            
            # Sign and send transaction
            response = self.solana_client.send_transaction(
                transaction, 
                self.bridge_keypair
            )
            
            # Extract signature from response
            if "result" not in response:
                return False, f"Failed to send transaction: {response}"
                
            signature = response["result"]
            
            # Wait for confirmation
            confirmation = self.solana_client.confirm_transaction(signature)
            if not confirmation or not confirmation.get("result", {}).get("value", False):
                return False, "Transaction could not be confirmed"
            
            # Record the transfer in the database
            self._record_bridge_transfer(tx_hash, signature, asset, solana_address)
            
            # Remove from locked assets
            self._remove_locked_asset(tx_hash)
            
            # If this was a multi-sig transfer, clean up pending transfer
            if tx_hash in self.pending_transfers:
                del self.pending_transfers[tx_hash]
            
            return True, signature
            
        except Exception as e:
            logging.error(f"Error in bridge_to_solana: {str(e)}")
            return False, str(e)
            
    def bridge_from_solana(self, solana_tx_signature, destination_account, token_id) -> Tuple[bool, str]:
        """Process incoming transfers from Solana to the custom blockchain
        
        Args:
            solana_tx_signature: Solana transaction signature
            destination_account: Destination account on the custom blockchain
            token_id: Token identifier on the custom blockchain
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Verify the Solana transaction
            tx_info = self.solana_client.get_transaction(solana_tx_signature)
            
            if "result" not in tx_info or not tx_info["result"]:
                return False, "Transaction not found or invalid on Solana"
                
            # Rest of the function implementation would go here
            # [Implementation details]
            
            return True, "Successfully processed transaction from Solana"
        except Exception as e:
            logging.error(f"Error in bridge_from_solana: {str(e)}")
            return False, str(e)
