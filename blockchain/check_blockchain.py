from marble_blockchain import (
    Block, Transaction, ProofOfHistory, ProofOfStake,
    MIN_STAKE_AMOUNT, BLOCK_TIME_TARGET, EPOCH_LENGTH, NETWORK_ID
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BlockchainCheck")

def check_blockchain_status():
    # Initialize components
    poh = ProofOfHistory()
    pos = ProofOfStake()
    
    # Get current PoH hash
    current_hash = poh.current_hash
    
    # Print status
    print("\nMarble Blockchain Status:")
    print("------------------------")
    print(f"Current PoH Hash: {current_hash}")
    print(f"PoH Throughput: {poh.get_throughput()} hashes/second")
    print(f"Active Validators: {len(pos.get_validator_set())}")
    print(f"Total Stake: {pos.total_stake}")
    print("\nConfiguration:")
    print(f"Minimum Stake Amount: {MIN_STAKE_AMOUNT}")
    print(f"Block Time Target: {BLOCK_TIME_TARGET}ms")
    print(f"Epoch Length: {EPOCH_LENGTH} slots")
    print(f"Network ID: {NETWORK_ID}")

if __name__ == "__main__":
    check_blockchain_status()

from marble_blockchain import (
    Block, Transaction, ProofOfHistory, ProofOfStake,
    MIN_STAKE_AMOUNT, BLOCK_TIME_TARGET, EPOCH_LENGTH, NETWORK_ID
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BlockchainCheck")

def check_blockchain_status():
    # Initialize components
    poh = ProofOfHistory()
    pos = ProofOfStake()
    
    # Get current PoH hash
    current_hash = poh.get_current_hash()
    
    # Print status
    print("\nMarble Blockchain Status:")
    print("------------------------")
    print(f"Current PoH Hash: {current_hash}")
    print(f"PoH Throughput: {poh.get_throughput()} hashes/second")
    print(f"Active Validators: {len(pos.get_validator_set())}")
    print(f"Total Stake: {pos.total_stake}")
    print("\nConfiguration:")
        # Get current PoH hash
        current_hash = poh.current_hash
    print(f"Epoch Length: {EPOCH_LENGTH} slots")
    print(f"Network ID: {NETWORK_ID}")

if __name__ == "__main__":
    check_blockchain_status()

