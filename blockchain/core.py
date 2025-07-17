import json
import os
from typing import Dict, List, Optional, Any, Union
from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_keys import keys
from eth_utils import to_checksum_address
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import RPC_URL, CHAIN_ID

class BlockchainInterface:
    """Core blockchain interface for DEX operations"""
    
    def __init__(self, rpc_url: str = RPC_URL, chain_id: int = CHAIN_ID):
        self.rpc_url = rpc_url
        self.chain_id = chain_id
        self.web3 = self._connect()
        self.contracts = {}
    
    def _connect(self) -> Web3:
        """Connect to the blockchain network"""
        web3 = Web3(Web3.HTTPProvider(self.rpc_url))
        # Add PoA middleware for networks like BSC, Polygon, etc.
        web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        if not web3.is_connected():
            raise ConnectionError(f"Failed to connect to the blockchain at {self.rpc_url}")
            
        return web3
    
    def create_account(self) -> LocalAccount:
        """Create a new blockchain account"""
        private_key = keys.PrivateKey(os.urandom(32))
        account = Account.from_key(private_key.to_hex())
        return account
    
    def load_account(self, private_key: str) -> LocalAccount:
        """Load an account from a private key"""
        return Account.from_key(private_key)
    
    def get_balance(self, address: str) -> float:
        """Get the native token balance of an address"""
        address = to_checksum_address(address)
        balance_wei = self.web3.eth.get_balance(address)
        return self.web3.from_wei(balance_wei, 'ether')
    
    def load_contract(self, contract_address: str, abi_path: str) -> None:
        """Load a smart contract"""
        contract_address = to_checksum_address(contract_address)
        
        # Load ABI from file
        with open(abi_path, 'r') as f:
            abi = json.load(f)
        
        # Create contract instance
        contract = self.web3.eth.contract(address=contract_address, abi=abi)
        self.contracts[contract_address] = contract
        return contract
    
    def get_token_balance(self, token_address: str, wallet_address: str) -> float:
        """Get ERC20 token balance"""
        token_address = to_checksum_address(token_address)
        wallet_address = to_checksum_address(wallet_address)
        
        if token_address not in self.contracts:
            # Standard ERC20 ABI for balanceOf function
            abi = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],
                    "name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],
                    "type":"function"}]
            token_contract = self.web3.eth.contract(address=token_address, abi=abi)
            self.contracts[token_address] = token_contract
        else:
            token_contract = self.contracts[token_address]
        
        balance_wei = token_contract.functions.balanceOf(wallet_address).call()
        # Try to get decimals, default to 18 if not available
        try:
            decimals = token_contract.functions.decimals().call()
        except:
            decimals = 18
        
        return balance_wei / (10 ** decimals)
    
    def estimate_gas(self, transaction) -> int:
        """Estimate gas for a transaction"""
        return self.web3.eth.estimate_gas(transaction)
    
    def send_transaction(self, transaction_data: Dict[str, Any], private_key: str) -> str:
        """Sign and send a transaction"""
        # Get the account from the private key
        account = Account.from_key(private_key)
        
        # Ensure the from address is set correctly
        transaction_data['from'] = account.address
        
        # If gas is not set, estimate it
        if 'gas' not in transaction_data:
            transaction_data['gas'] = self.estimate_gas(transaction_data)
        
        # Get the current nonce for the account
        transaction_data['nonce'] = self.web3.eth.get_transaction_count(account.address)
        
        # Sign the transaction
        signed_tx = self.web3.eth.account.sign_transaction(transaction_data, private_key)
        
        # Send the transaction
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        return tx_hash.hex()
    
    def get_transaction_receipt(self, tx_hash: str) -> Dict[str, Any]:
        """Get a transaction receipt"""
        return self.web3.eth.get_transaction_receipt(tx_hash)
    
    def deploy_contract(self, abi: List[Dict[str, Any]], bytecode: str, 
                        constructor_args: List[Any], private_key: str) -> str:
        """Deploy a new smart contract"""
        account = Account.from_key(private_key)
        
        # Create contract object
        contract = self.web3.eth.contract(abi=abi, bytecode=bytecode)
        
        # Build constructor transaction
        construct_txn = contract.constructor(*constructor_args).build_transaction({
            'from': account.address,
            'nonce': self.web3.eth.get_transaction_count(account.address),
            'gas': 2000000,  # Adjust as needed
            'gasPrice': self.web3.eth.gas_price,
            'chainId': self.chain_id
        })
        
        # Sign and send the transaction
        tx_hash = self.send_transaction(construct_txn, private_key)
        
        # Wait for the transaction to be mined
        tx_receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Return the contract address
        return tx_receipt.contractAddress

