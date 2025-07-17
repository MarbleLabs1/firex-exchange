#!/usr/bin/env python3
"""
Blockchain Command Line Interface

This script provides a user-friendly interface to interact with the blockchain system.
It offers functionality for:
- Adding transactions
- Mining new blocks
- Viewing the blockchain
- Searching transactions
- Displaying statistics
"""

import sys
import os
import json
import time
import hashlib
import uuid
import random
from datetime import datetime
from typing import List, Dict, Any, Optional

# Import blockchain components
from blockchain_core import Blockchain, Transaction, Block

class BlockchainCLI:
    """Command-line interface for interacting with the blockchain."""
    
    def __init__(self):
        """Initialize the blockchain and CLI state."""
        self.blockchain = Blockchain()
        self.wallet_address = f"user-{hashlib.sha256(str(time.time()).encode()).hexdigest()[:8]}"
        self.private_key = f"key-{uuid.uuid4()}"
        self.running = True
        print(f"\n🔑 Your wallet address: {self.wallet_address}")
        print(f"🔐 Your private key: {self.private_key}\n")
    
    def display_menu(self):
        """Display the main menu options."""
        print("\n" + "="*50)
        print("🔗 BLOCKCHAIN COMMAND LINE INTERFACE 🔗".center(50))
        print("="*50)
        print("1. Add Transaction")
        print("2. Mine Block")
        print("3. View Blockchain")
        print("4. Search Transactions")
        print("5. Display Blockchain Statistics")
        print("6. Exit")
        print("="*50)
    
    def add_transaction(self):
        """Add a new transaction to the blockchain."""
        print("\n📝 ADD NEW TRANSACTION")
        print("-"*50)
        
        try:
            recipient = input("Recipient address: ").strip()
            if not recipient:
                print("❌ Error: Recipient address cannot be empty.")
                return
            
            # Validate amount
            while True:
                try:
                    amount = float(input("Amount: ").strip())
                    if amount <= 0:
                        print("❌ Error: Amount must be positive.")
                        continue
                    break
                except ValueError:
                    print("❌ Error: Please enter a valid number for the amount.")
            
            # Optional data payload
            data_input = input("Data (optional, in JSON format): ").strip()
            if data_input:
                try:
                    data = json.loads(data_input)
                except json.JSONDecodeError:
                    print("⚠️ Warning: Invalid JSON format. Using data as plain text.")
                    data = {"message": data_input}
            else:
                data = {}
            
            # Create and add transaction
            tx = Transaction(
                sender=self.wallet_address,
                recipient=recipient,
                amount=amount,
                data=data
            )
            tx.sign(self.private_key)
            
            if self.blockchain.add_transaction(tx):
                print(f"✅ Transaction added successfully! Transaction ID: {tx.tx_id}")
            else:
                print("❌ Failed to add transaction. It may be invalid or the pool might be full.")
        
        except KeyboardInterrupt:
            print("\n⚠️ Transaction cancelled.")
        except Exception as e:
            print(f"❌ Error adding transaction: {e}")
    
    def mine_block(self):
        """Mine a new block with pending transactions."""
        print("\n⛏️ MINING NEW BLOCK")
        print("-"*50)
        
        try:
            # Check if there are pending transactions
            pending_count = len(self.blockchain.transaction_pool.get_transactions())
            if pending_count == 0:
                print("ℹ️ No pending transactions. Creating a block with coinbase transaction only.")
            else:
                print(f"ℹ️ Mining a block with {pending_count} pending transactions.")
            
            # Create and add the block
            print("⏳ Mining in progress...")
            start_time = time.time()
            
            new_block = self.blockchain.create_block(miner_address=self.wallet_address)
            success = self.blockchain.add_block(new_block)
            
            elapsed_time = time.time() - start_time
            
            if success:
                print(f"✅ Block #{new_block.index} mined successfully in {elapsed_time:.2f} seconds!")
                print(f"📊 Block hash: {new_block.hash}")
                print(f"📊 Number of transactions: {new_block.tx_count}")
            else:
                print("❌ Failed to add the mined block to the blockchain.")
        
        except KeyboardInterrupt:
            print("\n⚠️ Mining cancelled.")
        except Exception as e:
            print(f"❌ Error mining block: {e}")
    
    def view_blockchain(self):
        """View detailed information about the blockchain."""
        print("\n🔍 BLOCKCHAIN EXPLORER")
        print("-"*50)
        
        chain_length = self.blockchain.chain_length()
        print(f"📊 Chain length: {chain_length} blocks")
        
        # Display options for viewing
        print("\nView options:")
        print("1. Latest block")
        print("2. Block by index")
        print("3. Block by hash")
        print("4. All blocks (summary)")
        print("5. Back to main menu")
        
        try:
            choice = input("\nEnter your choice (1-5): ").strip()
            
            if choice == '1':
                # View latest block
                latest_block = self.blockchain.get_latest_block()
                self._display_block_details(latest_block)
            
            elif choice == '2':
                # View block by index
                try:
                    index = int(input(f"Enter block index (0-{chain_length-1}): ").strip())
                    block = self.blockchain.get_block_by_index(index)
                    if block:
                        self._display_block_details(block)
                    else:
                        print(f"❌ Block with index {index} not found.")
                except ValueError:
                    print("❌ Please enter a valid block index.")
            
            elif choice == '3':
                # View block by hash
                block_hash = input("Enter block hash: ").strip()
                block = self.blockchain.get_block_by_hash(block_hash)
                if block:
                    self._display_block_details(block)
                else:
                    print(f"❌ Block with hash {block_hash} not found.")
            
            elif choice == '4':
                # View all blocks (summary)
                print("\n📋 BLOCKCHAIN SUMMARY")
                print("-"*80)
                print(f"{'Index':<6} {'Timestamp':<25} {'Transactions':<12} {'Hash':<15}...")
                print("-"*80)
                
                for block in self.blockchain.chain:
                    timestamp = datetime.fromtimestamp(block.timestamp).strftime('%Y-%m-%d %H:%M:%S')
                    print(f"{block.index:<6} {timestamp:<25} {block.tx_count:<12} {block.hash[:15]}...")
            
            elif choice == '5':
                # Back to main menu
                return
            
            else:
                print("❌ Invalid choice.")
        
        except KeyboardInterrupt:
            print("\n⚠️ Operation cancelled.")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def _display_block_details(self, block: Block):
        """Display detailed information about a block."""
        timestamp = datetime.fromtimestamp(block.timestamp).strftime('%Y-%m-%d %H:%M:%S')
        
        print("\n📋 BLOCK DETAILS")
        print("-"*80)
        print(f"Block Index     : {block.index}")
        print(f"Timestamp       : {timestamp}")
        print(f"Hash            : {block.hash}")
        print(f"Previous Hash   : {block.previous_hash}")
        print(f"Merkle Root     : {block.merkle_root}")
        print(f"PoH Hash        : {block.poh_hash}")
        print(f"Transactions    : {block.tx_count}")
        print("-"*80)
        
        # Ask if user wants to see transactions
        if block.tx_count > 0:
            view_tx = input("View transactions? (y/n): ").lower().strip()
            if view_tx == 'y':
                print("\n📋 TRANSACTIONS IN BLOCK")
                print("-"*80)
                for i, tx in enumerate(block.transactions):
                    print(f"Transaction #{i+1}:")
                    print(f"  ID        : {tx.tx_id}")
                    print(f"  From      : {tx.sender}")
                    print(f"  To        : {tx.recipient}")
                    print(f"  Amount    : {tx.amount}")
                    if tx.data:
                        print(f"  Data      : {tx.data}")
                    timestamp = datetime.fromtimestamp(tx.timestamp).strftime('%Y-%m-%d %H:%M:%S')
                    print(f"  Timestamp : {timestamp}")
                    print("-"*40)
    
    def search_transactions(self):
        """Search for transactions by address."""
        print("\n🔍 SEARCH TRANSACTIONS")
        print("-"*50)
        
        try:
            address = input("Enter address to search for: ").strip()
            if not address:
                print("❌ Error: Address cannot be empty.")
                return
            
            print(f"\nSearching for transactions involving address: {address}")
            print("⏳ Please wait...")
            
            transactions = self.blockchain.search_transactions(address)
            
            if not transactions:
                print(f"ℹ️ No transactions found involving address {address}.")
                return
            
            print(f"\n✅ Found {len(transactions)} transactions:")
            print("-"*80)
            for i, tx in enumerate(transactions):
                tx_type = "SENT" if tx.sender == address else "RECEIVED"
                timestamp = datetime.fromtimestamp(tx.timestamp).strftime('%Y-%m-%d %H:%M:%S')
                
                print(f"Transaction #{i+1} ({tx_type}):")
                print(f"  ID        : {tx.tx_id}")
                print(f"  From      : {tx.sender}")
                print(f"  To        : {tx.recipient}")
                print(f"  Amount    : {tx.amount}")
                if tx.data:
                    print(f"  Data      : {tx.data}")
                print(f"  Timestamp : {timestamp}")
                print("-"*40)
        
        except KeyboardInterrupt:
            print("\n⚠️ Search cancelled.")
        except Exception as e:
            print(f"❌ Error searching transactions: {e}")
    
    def display_statistics(self):
        """Display blockchain statistics."""
        print("\n📊 BLOCKCHAIN STATISTICS")
        print("-"*50)
        
        try:
            chain_length = self.blockchain.chain_length()
            latest_block = self.blockchain.get_latest_block()
            pending_tx = len(self.blockchain.transaction_pool.get_transactions())
            poh_length = self.blockchain.poh.get_sequence_length()
            
            # Calculate total transactions
            total_tx = sum(block.tx_count for block in self.blockchain.chain)
            
            # Calculate average transactions per block
            avg_tx_per_block = total_tx / chain_length if chain_length > 0 else 0
            
            # Calculate blockchain age
            genesis_timestamp = self.blockchain.chain[0].timestamp
            latest_timestamp = latest_block.timestamp
            blockchain_age_seconds = latest_timestamp - genesis_timestamp
            blockchain_age_days = blockchain_age_seconds / (60 * 60 * 24)
            
            print(f"Chain Length         : {chain_length} blocks")
            print(f"Total Transactions   : {total_tx} transactions")
            print(f"Pending Transactions : {pending_tx} transactions")
            print(f"Avg. Tx per Block    : {avg_tx_per_block:.2f} transactions")
            print(f"PoH Sequence Length  : {poh_length} events")
            print(f"Blockchain Age       : {blockchain_age_days:.2f} days ({blockchain_age_seconds:.0f} seconds)")
            print(f"Latest Block Hash    : {latest_block.hash}")
            
            # Check chain validity
            print("\n⏳ Validating blockchain integrity...")
            valid = self.blockchain.validate_chain()
            if valid:
                print("✅ Blockchain is valid!")
            else:
                print("❌ Blockchain validation failed!")
        
        except Exception as e:
            print(f"❌ Error displaying statistics: {e}")
    
    def run(self):
        """Run the blockchain CLI main loop."""
        print("\n🚀 Welcome to the Blockchain Command Line Interface!")
        print("This interface allows you to interact with a high-throughput blockchain.")
        
        while self.running:
            try:
                self.display_menu()
                choice = input("\nEnter your choice (1-6): ").strip()
                
                if choice == '1':
                    self.add_transaction()
                elif choice == '2':
                    self.mine_block()
                elif choice == '3':
                    self.view_blockchain()
                elif choice == '4':
                    self.search_transactions()
                elif choice == '5':
                    self.display_statistics()
                elif choice == '6':
                    print("\n👋 Thank you for using the Blockchain CLI. Goodbye!")
                    self.running = False
                else:
                    print("❌ Invalid choice. Please enter a number between 1 and 6.")
            
            except KeyboardInterrupt:
                print("\n\n⚠️ Operation interrupted. Back to main menu.")
            except Exception as e:
                print(f"\n❌ An error occurred: {e}")
                print("Returning to main menu...")

if __name__ == "__main__":
    try:
        cli = BlockchainCLI()
        cli.run()
    except KeyboardInterrupt:
        print("\n\n👋 Program terminated by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)

