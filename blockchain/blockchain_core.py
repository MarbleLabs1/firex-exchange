import asyncio
import hashlib
import time
from typing import Dict, List, Optional, Any
import json
import logging
from dataclasses import dataclass
from datetime import datetime

from micro_os.vm.controller_native import VMController
from micro_os.network.p2p_vm import P2PNetworkManager, PeerMessage
from micro_os.ai.circuits import LensRefractor
from ai_module import AIContainerManager, ContainerSpec

@dataclass
class Block:
    index: int
    previous_hash: str
    timestamp: float
    data: Dict[str, Any]
    nonce: int
    hash: str = ""
    
    def calculate_hash(self) -> str:
        """Calculate the hash of the block."""
        block_string = f"{self.index}{self.previous_hash}{self.timestamp}{self.data}{self.nonce}"
        return hashlib.sha256(block_string.encode()).hexdigest()

class BlockchainNode:
    """
    Core blockchain node implementation that integrates with MicroOS components.
    Handles blockchain operations, P2P networking, and container management.
    """
    def __init__(self, node_id: str, host: str = "0.0.0.0", port: int = 8888):
        self.logger = logging.getLogger(__name__)
        self.node_id = node_id
        
        # Initialize MicroOS components
        self.vm_controller = VMController()
        self.network_manager = P2PNetworkManager(host_ip=host, port=port)
        self.ai_manager = AIContainerManager()
        self.lens_refractor = LensRefractor()
        
        # Blockchain state
        self.chain: List[Block] = []
        self.pending_transactions: List[Dict] = []
        self.peers: Dict[str, dict] = {}
        self.mining = False
        
        # Initialize handlers
        self._setup_message_handlers()

    async def start(self):
        """Start the blockchain node and its components."""
        try:
            # Start P2P network
            network_info = await self.network_manager.start()
            self.logger.info(f"P2P Network started: {network_info}")
            
            # Initialize blockchain if empty
            if not self.chain:
                await self._create_genesis_block()
            
            # Start mining process
            self.mining = True
            asyncio.create_task(self._mine_blocks())
            
            return {
                "node_id": self.node_id,
                "network": network_info,
                "chain_height": len(self.chain)
            }
        
        except Exception as e:
            self.logger.error(f"Failed to start blockchain node: {str(e)}", exc_info=True)
            raise RuntimeError(f"Node startup failed: {str(e)}")

    def _setup_message_handlers(self):
        """Set up handlers for different message types."""
        self.network_manager.add_message_handler("block", self._handle_new_block)
        self.network_manager.add_message_handler("transaction", self._handle_transaction)
        self.network_manager.add_message_handler("chain_request", self._handle_chain_request)

    async def _create_genesis_block(self):
        """Create and add the genesis block."""
        genesis_block = Block(
            index=0,
            previous_hash="0" * 64,
            timestamp=time.time(),
            data={"message": "Genesis Block"},
            nonce=0
        )
        genesis_block.hash = genesis_block.calculate_hash()
        self.chain.append(genesis_block)

    async def _mine_blocks(self):
        """Continuous mining process."""
        while self.mining:
            if self.pending_transactions:
                # Prepare new block
                new_block = await self._create_block()
                
                # Mine the block
                mined_block = await self._mine_block(new_block)
                
                if mined_block:
                    # Add to chain and broadcast
                    self.chain.append(mined_block)
                    await self._broadcast_block(mined_block)
                    
                    # Clear mined transactions
                    self.pending_transactions = self.pending_transactions[len(mined_block.data["transactions"]):]
            
            await asyncio.sleep(1)  # Mining interval

    async def _create_block(self) -> Block:
        """Create a new block with pending transactions."""
        last_block = self.chain[-1]
        return Block(
            index=len(self.chain),
            previous_hash=last_block.hash,
            timestamp=time.time(),
            data={
                "transactions": self.pending_transactions[:10],  # Process 10 transactions per block
                "miner": self.node_id
            },
            nonce=0
        )

    async def _mine_block(self, block: Block) -> Optional[Block]:
        """Mine a block with proof of work."""
        difficulty = 4  # Number of leading zeros required
        target = "0" * difficulty
        
        while self.mining:
            block.hash = block.calculate_hash()
            if block.hash.startswith(target):
                return block
            block.nonce += 1
            
            if block.nonce % 100000 == 0:  # Logging interval
                self.logger.debug(f"Mining... Nonce: {block.nonce}")
            
        return None

    async def _broadcast_block(self, block: Block):
        """Broadcast a mined block to the network."""
        message = PeerMessage(
            msg_type="block",
            payload={
                "block": {
                    "index": block.index,
                    "previous_hash": block.previous_hash,
                    "timestamp": block.timestamp,
                    "data": block.data,
                    "nonce": block.nonce,
                    "hash": block.hash
                }
            },
            timestamp=time.time(),
            sender=self.node_id
        )
        
        await self.network_manager.broadcast_vm_state(message.__dict__)

    async def _handle_new_block(self, message: PeerMessage):
        """Handle a new block received from the network."""
        block_data = message.payload["block"]
        new_block = Block(**block_data)
        
        # Verify block
        if await self._verify_block(new_block):
            if new_block.index == len(self.chain):
                self.chain.append(new_block)
                self.logger.info(f"Added new block {new_block.index}")
            elif new_block.index > len(self.chain):
                # We're behind, request full chain
                await self._request_chain(message.sender)

    async def _verify_block(self, block: Block) -> bool:
        """Verify a block's integrity and proof of work."""
        # Check hash calculation
        if block.hash != block.calculate_hash():
            return False
        
        # Check proof of work
        if not block.hash.startswith("0" * 4):  # Same difficulty as mining
            return False
        
        # If it's not the genesis block, check previous hash
        if block.index > 0:
            if block.index >= len(self.chain):
                return False
            if block.previous_hash != self.chain[block.index - 1].hash:
                return False
        
        return True

    async def _handle_transaction(self, message: PeerMessage):
        """Handle a new transaction received from the network."""
        transaction = message.payload["transaction"]
        # Add to pending transactions if valid
        if await self._verify_transaction(transaction):
            self.pending_transactions.append(transaction)

    async def _verify_transaction(self, transaction: Dict) -> bool:
        """Verify a transaction's validity."""
        # Implement transaction verification logic
        # For now, just basic structure checking
        required_fields = ["sender", "recipient", "amount", "signature"]
        return all(field in transaction for field in required_fields)

    async def _handle_chain_request(self, message: PeerMessage):
        """Handle a request for the full blockchain."""
        response = PeerMessage(
            msg_type="chain_response",
            payload={
                "chain": [
                    {
                        "index": block.index,
                        "previous_hash": block.previous_hash,
                        "timestamp": block.timestamp,
                        "data": block.data,
                        "nonce": block.nonce,
                        "hash": block.hash
                    }
                    for block in self.chain
                ]
            },
            timestamp=time.time(),
            sender=self.node_id
        )
        
        # Send chain to requesting peer
        await self.network_manager.broadcast_vm_state(response.__dict__)

    async def _request_chain(self, peer_id: str):
        """Request the full chain from a peer."""
        message = PeerMessage(
            msg_type="chain_request",
            payload={},
            timestamp=time.time(),
            sender=self.node_id
        )
        
        await self.network_manager.request_resources(message.__dict__)

    async def submit_transaction(self, transaction: Dict):
        """Submit a new transaction to the network."""
        if await self._verify_transaction(transaction):
            message = PeerMessage(
                msg_type="transaction",
                payload={"transaction": transaction},
                timestamp=time.time(),
                sender=self.node_id
            )
            
            # Add to pending transactions and broadcast
            self.pending_transactions.append(transaction)
            await self.network_manager.broadcast_vm_state(message.__dict__)
            
            return {"status": "accepted", "transaction": transaction}
        
        return {"status": "rejected", "reason": "Invalid transaction"}

    async def get_chain_status(self) -> Dict:
        """Get current blockchain status."""
        return {
            "height": len(self.chain),
            "latest_block": {
                "index": self.chain[-1].index,
                "hash": self.chain[-1].hash,
                "timestamp": self.chain[-1].timestamp
            },
            "pending_transactions": len(self.pending_transactions),
            "peers": len(self.peers)
        }

