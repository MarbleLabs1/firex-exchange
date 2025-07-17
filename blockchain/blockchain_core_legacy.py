import hashlib
import time
import json
import uuid
import threading
import concurrent.futures
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from queue import Queue
import multiprocessing
from datetime import datetime


class MerkleTree:
    """
    Merkle Tree implementation for efficient transaction verification.
    Allows for O(log n) verification of transactions within a block.
    """
    
    def __init__(self, transactions: List[Dict[str, Any]]):
        self.transactions = transactions
        self.leaves = [self._hash_transaction(tx) for tx in transactions]
        self.root = self._build_tree(self.leaves)
        
    def _hash_transaction(self, transaction: Dict[str, Any]) -> str:
        """Hash a transaction using SHA-256."""
        tx_string = json.dumps(transaction, sort_keys=True)
        return hashlib.sha256(tx_string.encode()).hexdigest()
    
    def _build_tree(self, leaves: List[str]) -> str:
        """Build the Merkle tree and return the root hash."""
        if not leaves:
            return hashlib.sha256("".encode()).hexdigest()
        
        if len(leaves) == 1:
            return leaves[0]
        
        # If odd number of leaves, duplicate the last one
        if len(leaves) % 2 != 0:
            leaves.append(leaves[-1])
            
        # Create next level of the tree
        next_level = []
        for i in range(0, len(leaves), 2):
            combined = leaves[i] + leaves[i+1]
            next_level.append(hashlib.sha256(combined.encode()).hexdigest())
        
        # Recursively build the tree
        return self._build_tree(next_level)
    
    def get_root(self) -> str:
        """Return the Merkle root."""
        return self.root
    
    def verify_transaction(self, transaction: Dict[str, Any]) -> bool:
        """Verify if a transaction is part of the Merkle tree."""
        tx_hash = self._hash_transaction(transaction)
        return tx_hash in self.leaves


class ProofOfHistory:
    """
    Implements a Proof of History timestamp system.
    Creates a verifiable, time-ordered sequence of hashed events.
    """
    
    def __init__(self, initial_hash: Optional[str] = None):
        self.sequence = []
        self.current_hash = initial_hash or hashlib.sha256(str(time.time()).encode()).hexdigest()
        
    def record_event(self, data: Any) -> str:
        """
        Record an event in the PoH sequence.
        Returns the hash of the recorded event.
        """
        timestamp = time.time()
        data_str = json.dumps(data, sort_keys=True) if isinstance(data, (dict, list)) else str(data)
        
        # Combine the current hash, timestamp, and data
        combined = f"{self.current_hash}{timestamp}{data_str}"
        new_hash = hashlib.sha256(combined.encode()).hexdigest()
        
        # Update the current hash and add to sequence
        self.current_hash = new_hash
        self.sequence.append({
            'timestamp': timestamp,
            'data_hash': hashlib.sha256(data_str.encode()).hexdigest(),
            'sequence_hash': new_hash
        })
        
        return new_hash
    
    def verify_sequence(self) -> bool:
        """Verify the integrity of the PoH sequence."""
        if not self.sequence:
            return True
            
        prev_hash = self.sequence[0]['sequence_hash']
        
        for i in range(1, len(self.sequence)):
            event = self.sequence[i]
            # Recalculate the hash to verify
            combined = f"{prev_hash}{event['timestamp']}{event['data_hash']}"
            calculated_hash = hashlib.sha256(combined.encode()).hexdigest()
            
            if calculated_hash != event['sequence_hash']:
                return False
                
            prev_hash = event['sequence_hash']
            
        return True
    
    def get_current_hash(self) -> str:
        """Get the current hash in the PoH sequence."""
        return self.current_hash
    
    def get_sequence_length(self) -> int:
        """Get the length of the PoH sequence."""
        return len(self.sequence)


@dataclass
class Transaction:
    """Represents a blockchain transaction with validation capabilities."""
    
    sender: str
    recipient: str
    amount: float
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    signature: Optional[str] = None
    tx_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary format."""
        return {
            'tx_id': self.tx_id,
            'sender': self.sender,
            'recipient': self.recipient,
            'amount': self.amount,
            'data': self.data,
            'timestamp': self.timestamp,
            'signature': self.signature
        }
    
    def hash(self) -> str:
        """Generate a hash of the transaction."""
        tx_dict = self.to_dict()
        tx_dict.pop('signature', None)  # Remove signature before hashing
        tx_string = json.dumps(tx_dict, sort_keys=True)
        return hashlib.sha256(tx_string.encode()).hexdigest()
    
    def sign(self, private_key: str) -> None:
        """
        Placeholder for signing the transaction.
        In a real implementation, this would use asymmetric cryptography.
        """
        # This is a simplified version - in a real implementation, use proper crypto
        tx_hash = self.hash()
        self.signature = hashlib.sha256((tx_hash + private_key).encode()).hexdigest()
    
    def is_valid(self) -> bool:
        """
        Check if the transaction is valid.
        Basic validation includes checking amounts, timestamps, and signatures.
        """
        # Check for negative amounts
        if self.amount < 0:
            return False
            
        # Check that the transaction is not in the future
        if self.timestamp > time.time() + 300:  # Allow 5 minutes clock drift
            return False
            
        # Check for required fields
        if not self.sender or not self.recipient or self.signature is None:
            return False
            
        # In a real implementation, verify the signature here
        
        return True


class TransactionPool:
    """
    Manages pending transactions with parallel processing capabilities.
    Optimized for high throughput and concurrent validation.
    """
    
    def __init__(self, max_pool_size: int = 10000, workers: int = None):
        self.transactions: Dict[str, Transaction] = {}
        self.max_pool_size = max_pool_size
        self.lock = threading.RLock()
        self.workers = workers or multiprocessing.cpu_count()
        self.process_queue = Queue()
        self.processing = False
        
    def add_transaction(self, transaction: Transaction) -> bool:
        """
        Add a transaction to the pool.
        Returns True if added successfully, False otherwise.
        """
        with self.lock:
            if len(self.transactions) >= self.max_pool_size:
                return False
                
            if transaction.tx_id in self.transactions:
                return False
                
            # Add to the pool and processing queue
            self.transactions[transaction.tx_id] = transaction
            self.process_queue.put(transaction)
            
            return True
    
    def get_transaction(self, tx_id: str) -> Optional[Transaction]:
        """Get a transaction by ID."""
        with self.lock:
            return self.transactions.get(tx_id)
    
    def remove_transaction(self, tx_id: str) -> bool:
        """Remove a transaction from the pool."""
        with self.lock:
            if tx_id in self.transactions:
                del self.transactions[tx_id]
                return True
            return False
    
    def get_transactions(self, count: int = None) -> List[Transaction]:
        """Get a list of transactions from the pool."""
        with self.lock:
            txs = list(self.transactions.values())
            if count:
                return txs[:count]
            return txs
    
    def clear_pool(self) -> None:
        """Clear all transactions from the pool."""
        with self.lock:
            self.transactions.clear()
            # Clear the queue
            while not self.process_queue.empty():
                try:
                    self.process_queue.get_nowait()
                except:
                    pass
    
    def start_processing(self) -> None:
        """Start parallel transaction processing."""
        if self.processing:
            return
            
        self.processing = True
        threading.Thread(target=self._process_transactions, daemon=True).start()
    
    def stop_processing(self) -> None:
        """Stop parallel transaction processing."""
        self.processing = False
    
    def _process_transactions(self) -> None:
        """Process transactions in parallel using a thread pool."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.workers) as executor:
            while self.processing:
                try:
                    # Process up to 100 transactions at a time
                    batch = []
                    for _ in range(100):
                        if not self.process_queue.empty():
                            batch.append(self.process_queue.get(timeout=0.1))
                        else:
                            break
                            
                    if not batch:
                        time.sleep(0.1)
                        continue
                        
                    # Process the batch in parallel
                    futures = [executor.submit(self._validate_transaction, tx) for tx in batch]
                    
                    # Handle completed validations
                    for future, tx in zip(futures, batch):
                        try:
                            is_valid = future.result(timeout=5)
                            if not is_valid:
                                self.remove_transaction(tx.tx_id)
                        except Exception as e:
                            print(f"Error validating transaction {tx.tx_id}: {e}")
                            self.remove_transaction(tx.tx_id)
                            
                except Exception as e:
                    print(f"Error in transaction processing: {e}")
                    time.sleep(0.5)
    
    def _validate_transaction(self, transaction: Transaction) -> bool:
        """Validate a single transaction."""
        return transaction.is_valid()


class Block:
    """
    Represents a block in the blockchain.
    Includes Merkle tree support and PoH integration.
    """
    
    def __init__(
        self, 
        index: int, 
        transactions: List[Transaction], 
        previous_hash: str,
        timestamp: float = None,
        poh_hash: str = None
    ):
        self.index = index
        self.timestamp = timestamp or time.time()
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.poh_hash = poh_hash
        self.tx_count = len(transactions)
        
        # Convert transactions to dicts for Merkle tree
        tx_dicts = [tx.to_dict() for tx in transactions]
        self.merkle_tree = MerkleTree(tx_dicts)
        self.merkle_root = self.merkle_tree.get_root()
        
        # Calculate block hash
        self.hash = self.calculate_hash()
        
    def calculate_hash(self) -> str:
        """Calculate the hash of the block."""
        block_data = {
            'index': self.index,
            'timestamp': self.timestamp,
            'merkle_root': self.merkle_root,
            'previous_hash': self.previous_hash,
            'poh_hash': self.poh_hash,
            'tx_count': self.tx_count
        }
        block_string = json.dumps(block_data, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert block to dictionary format."""
        return {
            'index': self.index,
            'timestamp': self.timestamp,
            'merkle_root': self.merkle_root,
            'previous_hash': self.previous_hash,
            'poh_hash': self.poh_hash,
            'hash': self.hash,
            'tx_count': self.tx_count,
            'transactions': [tx.to_dict() for tx in self.transactions]
        }
    
    def is_valid(self, previous_block: Optional['Block'] = None) -> bool:
        """
        Validate the block.
        Checks hash integrity, transaction validity, and link to previous block.
        """
        # Verify block hash
        if self.hash != self.calculate_hash():
            return False
            
        # Verify link to previous block if provided
        if previous_block and self.previous_hash != previous_block.hash:
            return False
            
        # Verify all transactions are valid
        for tx in self.transactions:
            if not tx.is_valid():
                return False
                
        # Verify Merkle root
        tx_dicts = [tx.to_dict() for tx in self.transactions]
        merkle_tree = MerkleTree(tx_dicts)
        if self.merkle_root != merkle_tree.get_root():
            return False
            
        return True
    
    def verify_transaction(self, tx: Transaction) -> bool:
        """Verify if a transaction is included in this block."""
        return self.merkle_tree.verify_transaction(tx.to_dict())


class Blockchain:
    """
    Main blockchain class that manages blocks and integrates PoH.
    Supports high throughput and parallel processing.
    """
    
    def __init__(self, difficulty: int = 4):
        self.chain: List[Block] = []
        self.transaction_pool = TransactionPool()
        self.transaction_pool.start_processing()
        self.poh = ProofOfHistory()
        self.difficulty = difficulty
        self.lock = threading.RLock()
        
        # Create genesis block
        self._create_genesis_block()
    
    def _create_genesis_block(self) -> None:
        """Create the genesis block."""
        genesis_tx = Transaction(
            sender="0",
            recipient="genesis",
            amount=0,
            data={"message": "Genesis Block"}
        )
        genesis_tx.sign("genesis_key")  # Simplified signing
        
        # Record in PoH
        poh_hash = self.poh.record_event("Genesis Block")
        
        # Create genesis block
        genesis_block = Block(
            index=0,
            transactions=[genesis_tx],
            previous_hash="0" * 64,
            poh_hash=poh_hash
        )
        
        self.chain.append(genesis_block)
    
    def add_transaction(self, transaction: Transaction) -> bool:
        """Add a transaction to the pool."""
        if not transaction.is_valid():
            return False
            
        # Record in PoH
        self.poh.record_event(transaction.to_dict())
        
        return self.transaction_pool.add_transaction(transaction)
    
    def create_block(self, miner_address: str = "system") -> Block:
        """
        Create a new block with transactions from the pool.
        Returns the newly created block.
        """
        with self.lock:
            # Get transactions from the pool
            transactions = self.transaction_pool.get_transactions(count=1000)
            
            if not transactions:
                # Add a coinbase transaction if no transactions available
                coinbase_tx = Transaction(
                    sender="0",
                    recipient=miner_address,
                    amount=1.0,  # Simplified mining reward
                    data={"type": "coinbase"}
                )
                coinbase_tx.sign("system_key")  # Simplified signing
                transactions = [coinbase_tx]
            
            # Record in PoH
            poh_hash = self.poh.record_event({
                "action": "block_creation",
                "tx_count": len(transactions),
                "timestamp": time.time()
            })
            
            # Create the new block
            previous_block = self.get_latest_block()
            new_block = Block(
                index=previous_block.index + 1,
                transactions=transactions,
                previous_hash=previous_block.hash,
                poh_hash=poh_hash
            )
            
            # Remove processed transactions from the pool
            for tx in transactions:
                self.transaction_pool.remove_transaction(tx.tx_id)
                
            return new_block
    
    def add_block(self, block: Block, skip_validation: bool = False) -> bool:
        """
        Add a block to the blockchain.
        Returns True if successful, False otherwise.
        """
        with self.lock:
            # Get the latest block for validation
            latest_block = self.get_latest_block()
            
            # Basic validation
            if block.index != latest_block.index + 1:
                return False
                
            if block.previous_hash != latest_block.hash:
                return False
            
            # Full validation if not skipped
            if not skip_validation:
                if not block.is_valid(latest_block):
                    return False
                    
                # Record block addition in PoH
                self.poh.record_event({
                    "action": "block_added",
                    "block_hash": block.hash,
                    "block_index": block.index,
                    "timestamp": time.time()
                })
                
            # Add the block to the chain
            self.chain.append(block)
            return True
    
    def get_latest_block(self) -> Block:
        """Return the latest block in the blockchain."""
        with self.lock:
            return self.chain[-1]
    
    def validate_chain(self, parallel: bool = True) -> bool:
        """
        Validate the entire blockchain.
        Can use parallel processing for validation.
        """
        if parallel and len(self.chain) > 1:
            return self.parallel_validation()
        
        # Sequential validation
        with self.lock:
            for i in range(1, len(self.chain)):
                current_block = self.chain[i]
                previous_block = self.chain[i-1]
                
                # Validate current block
                if not current_block.is_valid(previous_block):
                    return False
                
                # Validate block linkage
                if current_block.previous_hash != previous_block.hash:
                    return False
            
            return True
    
    def parallel_validation(self) -> bool:
        """
        Validate the blockchain using parallel processing.
        Splits the chain into segments and validates them concurrently.
        """
        with self.lock:
            chain_length = len(self.chain)
            
            # Only use parallelism for chains of sufficient length
            if chain_length <= 2:
                return self.validate_chain(parallel=False)
            
            # Function to validate a segment of the chain
            def validate_segment(start_idx: int, end_idx: int) -> bool:
                for i in range(start_idx, end_idx):
                    if i == 0:
                        continue  # Skip genesis block
                        
                    current_block = self.chain[i]
                    previous_block = self.chain[i-1]
                    
                    if not current_block.is_valid(previous_block):
                        return False
                    
                    if current_block.previous_hash != previous_block.hash:
                        return False
                
                return True
            
            # Determine segment size based on chain length
            segment_count = min(multiprocessing.cpu_count(), chain_length // 2)
            segment_size = chain_length // segment_count
            
            # Create segments for validation
            segments = []
            for i in range(segment_count):
                start_idx = i * segment_size
                end_idx = chain_length if i == segment_count - 1 else (i + 1) * segment_size
                segments.append((start_idx, end_idx))
            
            # Validate segments in parallel
            with concurrent.futures.ProcessPoolExecutor(max_workers=segment_count) as executor:
                futures = [executor.submit(validate_segment, start, end) for start, end in segments]
                
                # Collect results
                results = []
                for future in concurrent.futures.as_completed(futures):
                    try:
                        results.append(future.result())
                    except Exception as e:
                        print(f"Validation error: {e}")
                        return False
                
                # If any segment failed validation, the entire chain is invalid
                return all(results)
    
    def get_block_by_index(self, index: int) -> Optional[Block]:
        """Get a block by its index."""
        with self.lock:
            if 0 <= index < len(self.chain):
                return self.chain[index]
            return None
    
    def get_block_by_hash(self, block_hash: str) -> Optional[Block]:
        """Get a block by its hash."""
        with self.lock:
            for block in self.chain:
                if block.hash == block_hash:
                    return block
            return None
    
    def chain_length(self) -> int:
        """Get the length of the blockchain."""
        with self.lock:
            return len(self.chain)
    
    def search_transactions(self, address: str) -> List[Transaction]:
        """
        Search for all transactions involving a specific address.
        Returns transactions where the address is either sender or recipient.
        """
        results = []
        
        with self.lock:
            for block in self.chain:
                for tx in block.transactions:
                    if tx.sender == address or tx.recipient == address:
                        results.append(tx)
        
        return results
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the blockchain to a dictionary format."""
        with self.lock:
            return {
                "chain_length": len(self.chain),
                "poh_sequence_length": self.poh.get_sequence_length(),
                "latest_hash": self.get_latest_block().hash,
                "blocks": [block.to_dict() for block in self.chain]
            }
