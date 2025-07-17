import hashlib
import time
import json
from decimal import Decimal
import base58
import secrets
import sqlite3
import threading
import hmac
import random
from collections import defaultdict
import argparse  # For CLI

class CosmicAccount:
    def __init__(self, private_key=None):
        self.private_key = private_key or secrets.token_bytes(32)
        self.public_key = hashlib.sha256(self.private_key).digest()
        self.address = base58.b58encode(self.public_key).decode()
        self.stake = Decimal('0')
        self.stake_time = 0
        self.validator = False

    def sign(self, message):
        message_str = json.dumps(message, sort_keys=True).encode()
        return hmac.new(self.private_key, message_str, hashlib.sha256).hexdigest()

    def verify_signature(self, message, signature, public_key):
        message_str = json.dumps(message, sort_keys=True).encode()
        expected_sig = hmac.new(public_key, message_str, hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected_sig)

    def get_balance(self, token_id, db_path="cosmic.db"):
        conn = sqlite3.connect(db_path, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM balances WHERE account=? AND token_id=?", (self.address, token_id))
        result = cursor.fetchone()
        balance = Decimal(result[0]) if result else Decimal('0')
        conn.close()
        return balance

    def update_balance(self, token_id, amount, db_path="cosmic.db"):
        conn = sqlite3.connect(db_path, check_same_thread=False)
        cursor = conn.cursor()
        current = self.get_balance(token_id, db_path)
        new_balance = current + Decimal(str(amount))
        cursor.execute("INSERT OR REPLACE INTO balances (account, token_id, balance) VALUES (?, ?, ?)",
                       (self.address, token_id, str(new_balance)))
        conn.commit()
        conn.close()

    def stake_tokens(self, amount, db_path="cosmic.db"):
        energy_balance = self.get_balance("ENERGY", db_path)
        if energy_balance < amount:
            return False, "Insufficient ENERGY tokens"

        conn = sqlite3.connect(db_path, check_same_thread=False)
        cursor = conn.cursor()
        self.update_balance("ENERGY", -amount, db_path)
        self.stake += amount
        self.stake_time = time.time()
        self.validator = True

        cursor.execute("INSERT OR REPLACE INTO stakes (account, amount, timestamp) VALUES (?, ?, ?)",
                       (self.address, str(self.stake), self.stake_time))
        conn.commit()
        conn.close()
        return True, f"Staked {amount} ENERGY tokens"

    def unstake_tokens(self, amount, db_path="cosmic.db"):
        if self.stake < amount:
            return False, "Insufficient staked tokens"

        if time.time() - self.stake_time < 86400:  # Minimum staking period (24 hours)
            return False, "Cannot unstake before minimum staking period (24 hours)"

        conn = sqlite3.connect(db_path, check_same_thread=False)
        cursor = conn.cursor()

        self.stake -= amount
        if self.stake == 0:
            self.validator = False

        self.update_balance("ENERGY", amount, db_path)

        cursor.execute("INSERT OR REPLACE INTO stakes (account, amount, timestamp) VALUES (?, ?, ?)",
                       (self.address, str(self.stake), self.stake_time))
        conn.commit()
        conn.close()
        return True, f"Unstaked {amount} ENERGY tokens"


class CosmicBlock:
    def __init__(self, index, transactions, previous_hash, validator, shard_id=0):
        self.index = index
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.timestamp = time.time()
        self.validator = validator
        self.shard_id = shard_id
        self.signature = ""
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        data = json.dumps({
            "index": self.index,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "validator": self.validator,
            "shard_id": self.shard_id
        }, sort_keys=True).encode()
        return hashlib.sha256(data).hexdigest()

    def sign_block(self, private_key):
        block_data = json.dumps({
            "hash": self.hash,
            "validator": self.validator,
            "timestamp": self.timestamp
        }, sort_keys=True).encode()
        self.signature = hmac.new(private_key, block_data, hashlib.sha256).hexdigest()
        return self.signature

    def verify_block(self, public_key):
        block_data = json.dumps({
            "hash": self.hash,
            "validator": self.validator,
            "timestamp": self.timestamp
        }, sort_keys=True).encode()
        expected_sig = hmac.new(public_key, block_data, hashlib.sha256).hexdigest()
        return hmac.compare_digest(self.signature, expected_sig)


class CosmicBlockchain:
    def __init__(self, network, db_path="cosmic.db"):
        self.network = network
        self.db_path = db_path
        self.shard_count = 4
        self.shards = defaultdict(list)
        self.init_db()
        self.chain = [self.create_genesis()]
        self.accounts = {}
        self.tokens = {}
        self.pending_transactions = []
        self.validator_pool = []
        self.difficulty = 4
        self.reward = Decimal('5')
        self.min_fee = Decimal('0.01')
        self.validator_threshold = Decimal('100')

    def init_db(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS blocks (block_index INTEGER, shard_id INTEGER, data TEXT)")
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS balances (account TEXT, token_id TEXT, balance TEXT, PRIMARY KEY (account, token_id))")
        cursor.execute("CREATE TABLE IF NOT EXISTS stakes (account TEXT, amount TEXT, timestamp REAL, PRIMARY KEY (account))")
        cursor.execute("CREATE TABLE IF NOT EXISTS shards (shard_id INTEGER, last_block_index INTEGER)")
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS tokens (token_id TEXT PRIMARY KEY, name TEXT, symbol TEXT, decimals INTEGER, creator TEXT, timestamp REAL)")
        conn.commit()
        conn.close()

    def create_genesis(self):
        genesis_block = CosmicBlock(0, [{"type": "genesis", "data": {"message": "Genesis Block"}}], "0", "System")
        for shard_id in range(self.shard_count):
            shard_genesis = CosmicBlock(0, [{"type": "genesis", "data": {"message": f"Genesis for Shard {shard_id}"}}],
                                        "0", "System", shard_id)
            self.shards[shard_id].append(shard_genesis)

            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO shards (shard_id, last_block_index) VALUES (?, ?)", (shard_id, 0))
            cursor.execute("INSERT INTO blocks (block_index, shard_id, data) VALUES (?, ?, ?)",
                           (0, shard_id, json.dumps(vars(shard_genesis))))