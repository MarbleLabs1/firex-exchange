import unittest
import time
import hashlib
import multiprocessing
import random
import json
from concurrent.futures import ProcessPoolExecutor
from blockchain_core import Transaction, Block, Blockchain, TransactionPool, MerkleTree

class TestTransaction(unittest.TestCase):
    def test_transaction_creation(self):
        """Test that transactions are created with correct attributes"""
        sender = "sender_address"
        recipient = "recipient_address"
        amount = 10.0
        data = {"message": "Hello Blockchain"}
        
        tx = Transaction(sender, recipient, amount, data)
        
        self.assertEqual(tx.sender, sender)
        self.assertEqual(tx.recipient, recipient)
        self.assertEqual(tx.amount, amount)
        self.assertEqual(tx.data, data)
        self.assertIsNotNone(tx.timestamp)
        self.assertIsNotNone(tx.signature)
        self.assertIsNotNone(tx.transaction_id)
    
    def test_transaction_validation(self):
        """Test transaction validation logic"""
        tx = Transaction("sender", "recipient", 10.0, {"test": "data"})
        
        # Valid transaction
        self.assertTrue(tx.is_valid())
        
        # Test with tampered data
        tx_copy = Transaction("sender", "recipient", 10.0, {"test": "data"})
        tx_copy.transaction_id = tx.transaction_id
        tx_copy.timestamp = tx.timestamp
        tx_copy.signature = tx.signature
        tx_copy.amount = 20.0  # Tamper with amount
        
        self.assertFalse(tx_copy.is_valid())
    
    def test_transaction_to_dict(self):
        """Test transaction serialization to dictionary"""
        tx = Transaction("sender", "recipient", 10.0, {"test": "data"})
        tx_dict = tx.to_dict()
        
        self.assertIsInstance(tx_dict, dict)
        self.assertEqual(tx_dict["sender"], "sender")
        self.assertEqual(tx_dict["recipient"], "recipient")
        self.assertEqual(tx_dict["amount"], 10.0)
        self.assertEqual(tx_dict["data"]["test"], "data")


class TestBlock(unittest.TestCase):
    def setUp(self):
        """Create sample transactions for testing"""
        self.transactions = [
            Transaction("sender1", "recipient1", 10.0, {"data": "test1"}),
            Transaction("sender2", "recipient2", 20.0, {"data": "test2"}),
            Transaction("sender3", "recipient3", 30.0, {"data": "test3"})
        ]
    
    def test_block_creation(self):
        """Test that blocks are created with correct attributes"""
        prev_hash = "previous_hash_value"
        timestamp = time.time()
        
        block = Block(prev_hash, self.transactions, timestamp)
        
        self.assertEqual(block.previous_hash, prev_hash)
        self.assertEqual(len(block.transactions), 3)
        self.assertEqual(block.timestamp, timestamp)
        self.assertIsNotNone(block.merkle_root)
        self.assertIsNotNone(block.hash)
    
    def test_block_hash_calculation(self):
        """Test that block hash is calculated correctly"""
        prev_hash = "previous_hash_value"
        block = Block(prev_hash, self.transactions)
        
        # Calculate expected hash manually
        data_string = f"{prev_hash}{block.merkle_root}{block.timestamp}{block.nonce}"
        expected_hash = hashlib.sha256(data_string.encode()).hexdigest()
        
        self.assertEqual(block.calculate_hash(), expected_hash)
    
    def test_block_validation(self):
        """Test block validation logic"""
        prev_hash = "previous_hash_value"
        block = Block(prev_hash, self.transactions)
        
        # Valid block
        self.assertTrue(block.is_valid())
        
        # Tamper with a transaction
        block.transactions[0].amount = 999.0
        
        # Block should now be invalid due to merkle root mismatch
        self.assertFalse(block.is_valid())


class TestMerkleTree(unittest.TestCase):
    def setUp(self):
        """Create sample transactions for testing"""
        self.transactions = [
            Transaction("sender1", "recipient1", 10.0, {"data": "test1"}),
            Transaction("sender2", "recipient2", 20.0, {"data": "test2"}),
            Transaction("sender3", "recipient3", 30.0, {"data": "test3"}),
            Transaction("sender4", "recipient4", 40.0, {"data": "test4"})
        ]
        
        # Convert transactions to strings for Merkle tree
        self.tx_strings = [tx.transaction_id for tx in self.transactions]
    
    def test_merkle_tree_creation(self):
        """Test Merkle tree creation"""
        merkle_tree = MerkleTree(self.tx_strings)
        
        self.assertIsNotNone(merkle_tree.root)
        self.assertEqual(len(merkle_tree.leaves), 4)
    
    def test_merkle_root_calculation(self):
        """Test Merkle root calculation"""
        merkle_tree = MerkleTree(self.tx_strings)
        
        # Calculate expected root hash manually
        h1 = hashlib.sha256((self.tx_strings[0] + self.tx_strings[1]).encode()).hexdigest()
        h2 = hashlib.sha256((self.tx_strings[2] + self.tx_strings[3]).encode()).hexdigest()
        expected_root = hashlib.sha256((h1 + h2).encode()).hexdigest()
        
        self.assertEqual(merkle_tree.root, expected_root)
    
    def test_merkle_proof_verification(self):
        """Test Merkle proof verification"""
        merkle_tree = MerkleTree(self.tx_strings)
        
        # Get proof for the first transaction
        proof = merkle_tree.get_proof(self.tx_strings[0])
        
        # Verify the proof
        self.assertTrue(merkle_tree.verify_proof(self.tx_strings[0], proof, merkle_tree.root))
        
        # Test with invalid transaction
        invalid_tx = "invalid_transaction_id"
        self.assertFalse(merkle_tree.verify_proof(invalid_tx, proof, merkle_tree.root))


class TestBlockchain(unittest.TestCase):
    def setUp(self):
        """Create a blockchain instance for testing"""
        self.blockchain = Blockchain()
        
        # Create some sample transactions
        self.transactions = [
            Transaction("sender1", "recipient1", 10.0, {"data": "test1"}),
            Transaction("sender2", "recipient2", 20.0, {"data": "test2"}),
            Transaction("sender3", "recipient3", 30.0, {"data": "test3"})
        ]
    
    def test_genesis_block(self):
        """Test that the blockchain is initialized with a genesis block"""
        self.assertEqual(len(self.blockchain.chain), 1)
        self.assertEqual(self.blockchain.chain[0].previous_hash, "0")
    
    def test_add_block(self):
        """Test adding a block to the blockchain"""
        # Add transactions to the pool
        for tx in self.transactions:
            self.blockchain.transaction_pool.add_transaction(tx)
        
        # Create and add a new block
        new_block = self.blockchain.create_block()
        result = self.blockchain.add_block(new_block)
        
        self.assertTrue(result)
        self.assertEqual(len(self.blockchain.chain), 2)
        self.assertEqual(self.blockchain.chain[-1].hash, new_block.hash)
    
    def test_chain_validation(self):
        """Test blockchain validation"""
        # Add a valid block
        for tx in self.transactions:
            self.blockchain.transaction_pool.add_transaction(tx)
        
        self.blockchain.create_and_add_block()
        
        # Blockchain should be valid
        self.assertTrue(self.blockchain.is_chain_valid())
        
        # Tamper with a block
        self.blockchain.chain[1].transactions[0].amount = 999.0
        self.blockchain.chain[1].hash = self.blockchain.chain[1].calculate_hash()
        
        # Blockchain should now be invalid
        self.assertFalse(self.blockchain.is_chain_valid())
    
    def test_chain_replacement(self):
        """Test chain replacement with a longer valid chain"""
        # Create another blockchain instance with the same genesis block
        other_blockchain = Blockchain()
        other_blockchain.chain[0] = self.blockchain.chain[0]
        
        # Add transactions and blocks to the other blockchain to make it longer
        for i in range(3):
            tx = Transaction(f"sender{i}", f"recipient{i}", i*10.0, {"data": f"test{i}"})
            other_blockchain.transaction_pool.add_transaction(tx)
            other_blockchain.create_and_add_block()
        
        # Replace the chain
        result = self.blockchain.replace_chain(other_blockchain.chain)
        
        self.assertTrue(result)
        self.assertEqual(len(self.blockchain.chain), 4)  # Genesis + 3 new blocks


class TestTransactionPool(unittest.TestCase):
    def setUp(self):
        """Create a transaction pool instance for testing"""
        self.pool = TransactionPool()
        
        # Create some sample transactions
        self.transactions = [
            Transaction("sender1", "recipient1", 10.0, {"data": "test1"}),
            Transaction("sender2", "recipient2", 20.0, {"data": "test2"}),
            Transaction("sender3", "recipient3", 30.0, {"data": "test3"})
        ]
    
    def test_add_transaction(self):
        """Test adding a transaction to the pool"""
        for tx in self.transactions:
            result = self.pool.add_transaction(tx)
            self.assertTrue(result)
        
        self.assertEqual(len(self.pool.pending_transactions), 3)
    
    def test_get_transactions(self):
        """Test getting transactions from the pool"""
        for tx in self.transactions:
            self.pool.add_transaction(tx)
        
        # Get 2 transactions
        txs = self.pool.get_transactions(2)
        
        self.assertEqual(len(txs), 2)
        self.assertEqual(len(self.pool.pending_transactions), 1)
    
    def test_remove_transactions(self):
        """Test removing transactions from the pool"""
        for tx in self.transactions:
            self.pool.add_transaction(tx)
        
        # Remove specific transactions
        to_remove = [self.transactions[0], self.transactions[2]]
        self.pool.remove_transactions(to_remove)
        
        self.assertEqual(len(self.pool.pending_transactions), 1)
        self.assertEqual(self.pool.pending_transactions[0].transaction_id, 
                         self.transactions[1].transaction_id)


class TestParallelProcessing(unittest.TestCase):
    def setUp(self):
        """Create a blockchain instance for testing parallel processing"""
        self.blockchain = Blockchain()
        
        # Create a large number of transactions for parallel processing test
        self.large_tx_set = []
        for i in range(100):  # Smaller set for faster testing
            tx = Transaction(f"sender{i}", f"recipient{i}", 
                            i*10.0, {"data": f"test_data_{i}"})
            self.large_tx_set.append(tx)
    
    def test_parallel_transaction_validation(self):
        """Test parallel validation of transactions"""
        # Add all transactions to the pool
        for tx in self.large_tx_set:
            self.blockchain.transaction_pool.add_transaction(tx)
        
        # Validate transactions in parallel
        start_time = time.time()
        valid_txs = self.blockchain.parallel_validate_transactions(
            self.blockchain.transaction_pool.pending_transactions
        )
        parallel_time = time.time() - start_time
        
        # Validate transactions sequentially for comparison
        start_time = time.time()
        valid_txs_seq = []
        for tx in self.blockchain.transaction_pool.pending_transactions:
            if tx.is_valid():
                valid_txs_seq.append(tx)
        sequential_time = time.time() - start_time
        
        # Check that both methods return the same results
        self.assertEqual(len(valid_txs), len(valid_txs_seq))
        
        # For larger sets, parallel should be faster
        if len(self.large_tx_set) > 50:
            print(f"Parallel: {parallel_time:.4f}s, Sequential: {sequential_time:.4f}s")
            # This is not always true due to process creation overhead, 
            # especially for small sets, so we don't assert it
    
    def test_parallel_block_mining(self):
        """Test parallel mining of blocks"""
        # Add transactions to the pool
        for tx in self.large_tx_set[:20]:  # Use a subset
            self.blockchain.transaction_pool.add_transaction(tx)
        
        # Mine a block with parallel processing
        block = self.blockchain.create_block(use_parallel=True)
        
        self.assertIsNotNone(block)
        self.assertIsNotNone(block.hash)
        self.assertTrue(block.hash.startswith('0' * self.blockchain.difficulty))


if __name__ == "__main__":
    unittest.main()

