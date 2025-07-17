import argparse
from cosmic_blockchain import CosmicBlockchain
from smartcontract import CosmicDEX
from p2p_network import P2PNetwork
from solana_bridge import SolanaBridge
from POS_offgrid_ai import OffGridAI
from solana.keypair import Keypair

network = P2PNetwork()
blockchain = CosmicBlockchain(network)
dex = CosmicDEX(blockchain)
bridge = SolanaBridge(blockchain, dex)
ai = OffGridAI(blockchain)

def create_account(args):
    account = blockchain.register_account()
    print(f"Address: {account.address}\nPrivate Key: {account.private_key.hex()}")

def transfer(args):
    account = blockchain.accounts[args.account]
    tx_data = {"sender": account.address, "recipient": args.dest, "amount": args.amount}
    signature = account.sign(tx_data)
    blockchain.add_transaction("transfer", tx_data, signature)
    print("Transação enviada!")

def mine(args):
    if ai.enforce_rules() and blockchain.mine_block(args.account):
        print("Bloco minerado!")

def bridge(args):
    account = blockchain.accounts[args.account]
    solana_keypair = Keypair()
    tx_data = {"sender": account.address, "token_id": "ENERGY", "amount": args.amount}
    signature = account.sign(tx_data)
    tx_hash = bridge.lock_asset(account, "ENERGY", args.amount, signature)
    bridge.bridge_to_solana(tx_hash, solana_keypair)
    print(f"Bridged! Solana Address: {solana_keypair.public_key}")

parser = argparse.ArgumentParser(description="Marble Solana CLI")
subparsers = parser.add_subparsers()

parser_create = subparsers.add_parser("create", help="Cria uma nova conta")
parser_create.set_defaults(func=create_account)

parser_transfer = subparsers.add_parser("transfer", help="Transfere ENERGY")
parser_transfer.add_argument("account", help="Endereço da conta")
parser_transfer.add_argument("dest", help="Destino")
parser_transfer.add_argument("amount", type=float, help="Quantidade")
parser_transfer.set_defaults(func=transfer)

parser_mine = subparsers.add_parser("mine", help="Minera um bloco")
parser_mine.add_argument("account", help="Endereço do minerador")
parser_mine.set_defaults(func=mine)

parser_bridge = subparsers.add_parser("bridge", help="Bridge para Solana")
parser_bridge.add_argument("account", help="Endereço da conta")
parser_bridge.add_argument("amount", type=float, help="Quantidade")
parser_bridge.set_defaults(func=bridge)

args = parser.parse_args()
args.func(args)