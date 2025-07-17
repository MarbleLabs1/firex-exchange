# -*- coding: utf-8 -*-
# C:\Users\Work\Desktop\DEX SOL MARBL\smartcontract.py
from decimal import Decimal, getcontext
getcontext().prec = 28
import sqlite3

class CosmicToken:
    def __init__(self, token_id, name, symbol, decimals):
        self.token_id = token_id
        self.name = name
        self.symbol = symbol
        self.decimals = decimals

class LiquidityPoolContract:
    def __init__(self, blockchain, token_a, token_b, contract_id, db_path="cosmic.db"):
        self.blockchain = blockchain
        self.token_a = token_a
        self.token_b = token_b
        self.contract_id = contract_id
        self.pool_id = f"{token_a.token_id}_{token_b.token_id}"
        self.db_path = db_path
        self.state = {"reserve_a": Decimal('0'), "reserve_b": Decimal('0')}
        self.load_reserves()

    def load_reserves(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT reserve_a, reserve_b FROM pools WHERE pool_id=?", (self.pool_id,))
        result = cursor.fetchone()
        self.state["reserve_a"] = Decimal(result[0]) if result else Decimal('0')
        self.state["reserve_b"] = Decimal(result[1]) if result else Decimal('0')
        conn.close()

    def save_reserves(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO pools (pool_id, reserve_a, reserve_b) VALUES (?, ?, ?)",
                       (self.pool_id, str(self.state["reserve_a"]), str(self.state["reserve_b"])))
        conn.commit()
        conn.close()

    def add_liquidity(self, sender, amount_a, amount_b):
        if sender.get_balance(self.token_a.token_id, self.db_path) < amount_a:
            return False, "Insufficient token A balance"
        if sender.get_balance(self.token_b.token_id, self.db_path) < amount_b:
            return False, "Insufficient token B balance"
        
        sender.update_balance(self.token_a.token_id, -amount_a, self.db_path)
        sender.update_balance(self.token_b.token_id, -amount_b, self.db_path)
        self.state["reserve_a"] += amount_a
        self.state["reserve_b"] += amount_b
        self.save_reserves()
        return True, f"Added {amount_a} {self.token_a.token_id} and {amount_b} {self.token_b.token_id} to pool"

    def swap(self, sender, token_in, amount_in):
        if token_in == self.token_a.token_id:
            reserve_in = self.state["reserve_a"]
            reserve_out = self.state["reserve_b"]
            token_out = self.token_b.token_id
        elif token_in == self.token_b.token_id:
            reserve_in = self.state["reserve_b"]
            reserve_out = self.state["reserve_a"]
            token_out = self.token_a.token_id
        else:
            return False, "Invalid token"

        if sender.get_balance(token_in, self.db_path) < amount_in:
            return False, "Insufficient balance"
        
        amount_out = (amount_in * reserve_out) / (reserve_in + amount_in)
        sender.update_balance(token_in, -amount_in, self.db_path)
        sender.update_balance(token_out, amount_out, self.db_path)
        if token_in == self.token_a.token_id:
            self.state["reserve_a"] += amount_in
            self.state["reserve_b"] -= amount_out
        else:
            self.state["reserve_b"] += amount_in
            self.state["reserve_a"] -= amount_out
        self.save_reserves()
        return True, f"Swapped {amount_in} {token_in} for {amount_out} {token_out}"

class SmartContractManager:
    def __init__(self, blockchain, db_path="cosmic.db"):
        self.blockchain = blockchain
        self.db_path = db_path
        self.contracts = {}
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS pools (pool_id TEXT PRIMARY KEY, reserve_a TEXT, reserve_b TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS contracts (contract_id TEXT PRIMARY KEY, type TEXT, data TEXT)")
        conn.commit()
        conn.close()

    def deploy_contract(self, sender, contract_type, params):
        contract_id = f"{sender.address}_{len(self.contracts)}"
        if contract_type == "liquidity_pool":
            token_a = self.blockchain.tokens.get(params["token_a_id"]) or self.blockchain.register_token(
                params["token_a_id"], params["token_a_id"], params["token_a_id"], 6)
            token_b = self.blockchain.tokens.get(params["token_b_id"]) or self.blockchain.register_token(
                params["token_b_id"], params["token_b_id"], params["token_b_id"], 6)
            contract = LiquidityPoolContract(self.blockchain, token_a, token_b, contract_id, self.db_path)
            self.contracts[contract_id] = contract
            return contract_id, "Liquidity pool contract deployed"
        elif contract_type == "transfer":
            # Simple transfer contract example
            contract = {"type": "transfer", "state": {}}
            self.contracts[contract_id] = contract
            return contract_id, "Transfer contract deployed"
        return None, "Unknown contract type"

    def execute_contract(self, sender, contract_id, action, params):
        contract = self.contracts.get(contract_id)
        if not contract:
            return False, "Contract not found"
        
        if isinstance(contract, LiquidityPoolContract):
            if action == "add_liquidity":
                return contract.add_liquidity(sender, params["amount_a"], params["amount_b"])
            elif action == "swap":
                return contract.swap(sender, params["token_in"], params["amount_in"])
        elif isinstance(contract, dict) and contract["type"] == "transfer":
            if action == "transfer":
                from_addr = sender.address
                to_addr = params["to"]
                amount = params["amount"]
                token_id = params.get("token_id", "ENERGY")
                if sender.get_balance(token_id, self.db_path) >= amount:
                    sender.update_balance(token_id, -amount, self.db_path)
                    self.blockchain.accounts[to_addr].update_balance(token_id, amount, self.db_path)
                    contract["state"]["last_transfer"] = {"from": from_addr, "to": to_addr, "amount": amount}
                    return True, "Transfer executed"
                return False, "Insufficient balance"
        return False, "Invalid action or contract type"

    def register_token(self, token_id, name, symbol, decimals):
        return self.blockchain.register_token(token_id, name, symbol, decimals)