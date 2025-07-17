#!/usr/bin/env python3
"""
Solana CLI - A command-line interface for interacting with the Solana blockchain

This file provides various functions to interact with Solana networks:
- Connect to different networks (mainnet, testnet, devnet)
- Check account balances
- Make transactions between accounts
- Retrieve transaction history

Requirements:
pip install solana base58 construct
"""

import json
import argparse
from typing import List, Dict, Optional, Any, Union
from pathlib import Path

from solana.rpc.api import Client
from solana.rpc.types import TxOpts
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.transaction import Transaction
from solana.system_program import SYS_PROGRAM_ID, TransferParams, transfer
from solana.rpc.commitment import Confirmed
from spl.token.client import Token
from spl.token.constants import TOKEN_PROGRAM_ID

# Constants
LAMPORTS_PER_SOL = 1_000_000_000

# Network configuration
NETWORKS = {
    "MAINNET": "https://api.mainnet-beta.solana.com",
    "TESTNET": "https://api.testnet.solana.com",
    "DEVNET": "https://api.devnet.solana.com",
    "LOCALNET": "http://127.0.0.1:8899"
}

current_network = NETWORKS["DEVNET"]
connection = Client(current_network)


def set_network(network: str) -> Optional[Client]:
    """
    Set the Solana network to connect to
    
    Args:
        network: The network to connect to (mainnet-beta, testnet, devnet, or localnet)
        
    Returns:
        The connection object or None if invalid network
    """
    global current_network, connection
    
    if network == "localnet":
        current_network = NETWORKS["LOCALNET"]
        connection = Client(current_network)
    elif network in ["mainnet-beta", "testnet", "devnet"]:
        network_key = network.upper() if network != "mainnet-beta" else "MAINNET"
        current_network = NETWORKS[network_key]
        connection = Client(current_network)
    else:
        print(f"Invalid network: {network}. Valid options are: mainnet-beta, testnet, devnet, localnet")
        return None
    
    print(f"Connected to {network}")
    return connection


def load_keypair(file_path: str) -> Optional[Keypair]:
    """
    Load a keypair from a file
    
    Args:
        file_path: Path to the keypair JSON file
        
    Returns:
        The loaded keypair or None if error
    """
    try:
        with open(file_path, 'r') as f:
            keypair_data = json.load(f)
        
        # Convert JSON keypair to bytes
        secret_key = bytes(keypair_data)
        return Keypair.from_secret_key(secret_key)
    except Exception as e:
        print(f"Error loading keypair: {e}")
        return None


async def get_balance(public_key_str: str) -> Optional[float]:
    """
    Get the balance of a Solana account
    
    Args:
        public_key_str: The public key of the account
        
    Returns:
        The balance in SOL or None if error
    """
    try:
        public_key = PublicKey(public_key_str)
        balance_response = connection.get_balance(public_key)
        if balance_response["result"]["value"] is not None:
            return balance_response["result"]["value"] / LAMPORTS_PER_SOL
        return 0
    except Exception as e:
        print(f"Error fetching balance: {e}")
        return None


async def get_account_info(public_key_str: str) -> Optional[Dict]:
    """
    Get account info
    
    Args:
        public_key_str: The public key of the account
        
    Returns:
        Account info or None if error
    """
    try:
        public_key = PublicKey(public_key_str)
        account_info = connection.get_account_info(public_key)
        return account_info["result"]["value"]
    except Exception as e:
        print(f"Error fetching account info: {e}")
        return None


async def send_sol(from_keypair: Keypair, to_public_key_str: str, amount: float) -> Optional[str]:
    """
    Send SOL from one account to another
    
    Args:
        from_keypair: The keypair of the sender
        to_public_key_str: The public key of the recipient
        amount: The amount of SOL to send
        
    Returns:
        Transaction signature or None if error
    """
    try:
        to_public_key = PublicKey(to_public_key_str)
        
        # Create a transfer instruction
        transfer_params = TransferParams(
            from_pubkey=from_keypair.public_key,
            to_pubkey=to_public_key,
            lamports=int(amount * LAMPORTS_PER_SOL)
        )
        
        transaction = Transaction().add(transfer(transfer_params))
        
        # Sign and send transaction
        tx_opts = TxOpts(skip_preflight=False, skip_confirmation=False)
        signature = connection.send_transaction(
            transaction, 
            from_keypair, 
            opts=tx_opts
        )
        
        result = signature["result"]
        network_suffix = "?cluster=" + current_network.split(".")[-2].split("-")[0]
        print(f"Transaction sent: https://explorer.solana.com/tx/{result}{network_suffix}")
        return result
    except Exception as e:
        print(f"Error sending SOL: {e}")
        return None


async def request_airdrop(public_key_str: str, amount: float) -> Optional[str]:
    """
    Request an airdrop of SOL (only works on devnet and testnet)
    
    Args:
        public_key_str: The public key to receive SOL
        amount: The amount of SOL to request
        
    Returns:
        Transaction signature or None if error
    """
    if current_network == NETWORKS["MAINNET"]:
        print("Airdrops are not available on mainnet")
        return None
    
    try:
        public_key = PublicKey(public_key_str)
        airdrop_response = connection.request_airdrop(
            public_key,
            int(amount * LAMPORTS_PER_SOL)
        )
        
        signature = airdrop_response["result"]
        network_suffix = "?cluster=" + current_network.split(".")[-2].split("-")[0]
        
        # Wait for confirmation
        connection.confirm_transaction(signature)
        print(f"Airdrop successful: https://explorer.solana.com/tx/{signature}{network_suffix}")
        return signature
    except Exception as e:
        print(f"Error requesting airdrop: {e}")
        return None


async def get_transaction_history(public_key_str: str, limit: int = 10) -> List:
    """
    Get transaction history for an account
    
    Args:
        public_key_str: The public key of the account
        limit: Maximum number of transactions to fetch
        
    Returns:
        Array of transactions
    """
    try:
        public_key = PublicKey(public_key_str)
        signatures_response = connection.get_signatures_for_address(
            public_key,
            limit=limit
        )
        
        signatures = signatures_response["result"]
        transactions = []
        
        for sig_info in signatures:
            tx_response = connection.get_transaction(
                sig_info["signature"]
            )
            transactions.append(tx_response["result"])
        
        return transactions
    except Exception as e:
        print(f"Error fetching transaction history: {e}")
        return []


async def get_token_accounts(owner_public_key_str: str) -> List:
    """
    Get token accounts owned by an address
    
    Args:
        owner_public_key_str: The public key of the owner
        
    Returns:
        Array of token accounts
    """
    try:
        owner_public_key = PublicKey(owner_public_key_str)
        accounts_response = connection.get_token_accounts_by_owner(
            owner_public_key,
            {"programId": TOKEN_PROGRAM_ID}
        )
        
        token_accounts = []
        for account_info in accounts_response["result"]["value"]:
            # Parse account data
            pubkey = account_info["pubkey"]
            account_data = account_info["account"]["data"]
            # More detailed parsing would be needed here for actual data extraction
            # This is a simplified version
            token_accounts.append({
                "pubkey": pubkey,
                "data": account_data
            })
        
        return token_accounts
    except Exception as e:
        print(f"Error fetching token accounts: {e}")
        return []


async def get_network_status() -> Optional[Dict]:
    """
    Get current Solana network status
    
    Returns:
        Network status info
    """
    try:
        version_response = connection.get_version()
        version = version_response["result"]
        
        slot_response = connection.get_slot()
        slot = slot_response["result"]
        
        supply_response = connection.get_supply()
        supply = supply_response["result"]["value"]
        
        epoch_info_response = connection.get_epoch_info()
        epoch_info = epoch_info_response["result"]
        
        return {
            "network": current_network,
            "version": version,
            "currentSlot": slot,
            "totalSupply": supply["total"] / LAMPORTS_PER_SOL,
            "epoch": epoch_info["epoch"],
            "slotInEpoch": epoch_info["slotIndex"],
            "slotsInEpoch": epoch_info["slotsInEpoch"],
            "epochProgress": f"{(epoch_info['slotIndex'] / epoch_info['slotsInEpoch'] * 100):.2f}%"
        }
    except Exception as e:
        print(f"Error fetching network status: {e}")
        return None


# Command-line interface
def setup_cli():
    """Set up the command-line interface"""
    parser = argparse.ArgumentParser(description="Solana CLI - Interact with the Solana blockchain")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Network command
    network_parser = subparsers.add_parser("network", help="Get or set the current network")
    network_parser.add_argument("network", nargs="?", help="Network to connect to (mainnet-beta, testnet, devnet, localnet)")
    
    # Balance command
    balance_parser = subparsers.add_parser("balance", help="Get the balance of an account")
    balance_parser.add_argument("public_key", help="Public key of the account")
    
    # Airdrop command
    airdrop_parser = subparsers.add_parser("airdrop", help="Request an airdrop of SOL (devnet/testnet only)")
    airdrop_parser.add_argument("public_key", help="Public key to receive SOL")
    airdrop_parser.add_argument("amount", type=float, help="Amount of SOL to request")
    
    # Send command
    send_parser = subparsers.add_parser("send", help="Send SOL to another account")
    send_parser.add_argument("keypair_path", help="Path to sender's keypair file")
    send_parser.add_argument("to_public_key", help="Recipient's public key")
    send_parser.add_argument("amount", type=float, help="Amount of SOL to send")
    
    # History command
    history_parser = subparsers.add_parser("history", help="Get transaction history for an account")
    history_parser.add_argument("public_key", help="Public key of the account")
    history_parser.add_argument("limit", nargs="?", type=int, default=10, help="Maximum number of transactions to fetch")
    
    # Token accounts command
    tokens_parser = subparsers.add_parser("tokens", help="Get token accounts owned by an address")
    tokens_parser.add_argument("public_key", help="Public key of the owner")
    
    # Status command
    subparsers.add_parser("status", help="Get current network status")
    
    return parser


async def main():
    """Main entry point for the CLI"""
    parser = setup_cli()
    args = parser.parse_args()
    
    if args.command == "network":
        if args.network:
            set_network(args.network)
        else:
            print(f"Current network: {current_network}")
    
    elif args.command == "balance":
        balance = await get_balance(args.public_key)
        if balance is not None:
            print(f"Balance: {balance} SOL")
    
    elif args.command == "airdrop":
        await request_airdrop(args.public_key, args.amount)
    
    elif args.command == "send":
        keypair = load_keypair(args.keypair_path)
        if keypair:
            await send_sol(keypair, args.to_public_key, args.amount)
    
    elif args.command == "history":
        transactions = await get_transaction_history(args.public_key, args.limit)
        print(json.dumps(transactions, indent=2))
    
    elif args.command == "tokens":
        token_accounts = await get_token_accounts(args.public_key)
        print(json.dumps(token_accounts, indent=2))
    
    elif args.command == "status":
        status = await get_network_status()
        print(json.dumps(status, indent=2))
    
    else:
        parser.print_help()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

