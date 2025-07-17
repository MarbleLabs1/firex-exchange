# -*- coding: utf-8 -*-
# C:\Users\Work\Desktop\DEX SOL MARBL\main.py
import os
import webbrowser
import threading
import time
from waitress import serve
from cosmic_blockchain import CosmicBlockchain, CosmicAccount, CosmicBlock
from smartcontract import SmartContractManager, CosmicToken
from dex_web import application as app, blockchain, explorer, pool_contract_id
from "IA regen run (1)" import RegenerativeDeepSeekAI

# Mock missing dependencies
class MockP2PNetwork:
    def __init__(self):
        pass
    def send_message(self, message):
        print(f"Mock network sending: {message}")

class MockSolanaBridge:
    def __init__(self, blockchain, contract_manager):
        pass
    def lock_asset(self, account, token_id, amount, signature):
        print(f"Mock locking {amount} {token_id} for {account.address}")
        return "mock_tx_hash"
    def bridge_to_solana(self, tx_hash, solana_keypair, solana_address):
        print(f"Mock bridging {tx_hash} to Solana address: {solana_address}")
        return True

# Replaced with RegenerativeDeepSeekAI
# class MockOffGridAI:
#     def __init__(self, blockchain):
#         pass

# Override dex_web.py dependencies
import dex_web
dex_web.network = MockP2PNetwork()
# Use a persistent database file
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cosmic_blockchain.db")
dex_web.blockchain = CosmicBlockchain(dex_web.network, db_path=db_path)
dex_web.explorer = CosmicAccount()
dex_web.contract_manager = SmartContractManager(dex_web.blockchain)
dex_web.bridge = MockSolanaBridge(dex_web.blockchain, dex_web.contract_manager)
dex_web.ai = RegenerativeDeepSeekAI(model_name="deepseek-ai/DeepSeek-R1", db_path="ai_blockchain.sqlite")

def open_browser():
    time.sleep(2)  # Give the server a moment to start
    webbrowser.open('http://localhost:5000')
    
def main():
    print("Starting Marble Blockchain...")
    
    # Initialize the blockchain
    print(f"Blockchain initialized with database at: {dex_web.blockchain.db_path}")
    
    # Explorer balances are displayed in the web UI
    
    # Start browser in a separate thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Start the web server
    print("Starting web server at http://localhost:5000")
    serve(app, host="localhost", port=5000)

if __name__ == "__main__":
    main()