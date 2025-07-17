import asyncio
import json
import logging
from typing import Dict, List, Optional, Tuple
import aioice
from dataclasses import dataclass
from datetime import datetime

@dataclass
class PeerConnection:
    peer_id: str
    ice_connection: aioice.Connection
    stun_candidates: List[aioice.Candidate]
    local_candidates: List[aioice.Candidate]
    connected: bool = False
    last_seen: float = 0.0

class NetworkManager:
    """
    Manages network connections with NAT traversal support using ICE/STUN.
    Handles peer discovery and connection management.
    """
    def __init__(self, stun_servers: List[str] = None):
        self.logger = logging.getLogger(__name__)
        self.stun_servers = stun_servers or [
            "stun:stun.l.google.com:19302",
            "stun:stun1.l.google.com:19302",
        ]
        self.peers: Dict[str, PeerConnection] = {}
        self.ice_controlling = True
        self._setup_ice_config()

    def _setup_ice_config(self):
        """Set up ICE configuration with STUN servers."""
        self.ice_config = aioice.ICEGatherer(
            servers=[
                aioice.StunServer(server) for server in self.stun_servers
            ]
        )

    async def start(self):
        """Start the network manager and ICE gatherer."""
        try:
            await self.ice_config.gather()
            self.logger.info("ICE gathering completed")
            return {
                "local_candidates": [
                    str(c) for c in self.ice_config.local_candidates
                ]
            }
        except Exception as e:
            self.logger.error(f"Failed to start network manager: {str(e)}")
            raise RuntimeError(f"Network start failed: {str(e)}")

    async def create_peer_connection(self, peer_id: str) -> PeerConnection:
        """Create a new peer connection with ICE support."""
        try:
            # Create ICE connection
            connection = aioice.Connection(
                ice_controlling=self.ice_controlling,
                components=1
            )
            
            # Get local candidates
            local_candidates = await connection.get_local_candidates()
            
            peer_conn = PeerConnection(
                peer_id=peer_id,
                ice_connection=connection,
                stun_candidates=[],
                local_candidates=local_candidates
            )
            
            self.peers[peer_id] = peer_conn
            return peer_conn
        
        except Exception as e:
            self.logger.error(f"Failed to create peer connection: {str(e)}")
            raise RuntimeError(f"Peer connection creation failed: {str(e)}")

    async def connect_to_peer(self, peer_id: str, 
                            remote_candidates: List[str]) -> bool:
        """Establish connection to a peer using ICE."""
        try:
            if peer_id not in self.peers:
                peer_conn = await self.create_peer_connection(peer_id)
            else:
                peer_conn = self.peers[peer_id]
            
            # Convert remote candidate strings to Candidate objects
            remote_candidates = [
                aioice.Candidate.from_sdp(c) for c in remote_candidates
            ]
            
            # Add remote candidates
            for candidate in remote_candidates:
                await peer_conn.ice_connection.add_remote_candidate(candidate)
            
            # Start connection
            await peer_conn.ice_connection.connect()
            
            peer_conn.connected = True
            peer_conn.last_seen = datetime.now().timestamp()
            
            self.logger.info(f"Connected to peer {peer_id}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to connect to peer {peer_id}: {str(e)}")
            return False

    async def send_data(self, peer_id: str, data: dict) -> bool:
        """Send data to a peer through the established ICE connection."""
        try:
            if peer_id not in self.peers or not self.peers[peer_id].connected:
                return False
            
            peer_conn = self.peers[peer_id]
            data_str = json.dumps(data)
            
            # Send data through ICE connection
            await peer_conn.ice_connection.send(data_str.encode())
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to send data to peer {peer_id}: {str(e)}")
            return False

    async def receive_data(self, peer_id: str) -> Optional[dict]:
        """Receive data from a peer through the ICE connection."""
        try:
            if peer_id not in self.peers or not self.peers[peer_id].connected:
                return None
            
            peer_conn = self.peers[peer_id]
            data = await peer_conn.ice_connection.receive()
            
            if data:
                return json.loads(data.decode())
            return None
        
        except Exception as e:
            self.logger.error(f"Failed to receive data from peer {peer_id}: {str(e)}")
            return None

    async def handle_connection_loss(self, peer_id: str):
        """Handle loss of connection to a peer."""
        try:
            if peer_id in self.peers:
                peer_conn = self.peers[peer_id]
                await peer_conn.ice_connection.close()
                del self.peers[peer_id]
                self.logger.info(f"Disconnected from peer {peer_id}")
        
        except Exception as e:
            self.logger.error(f"Error handling connection loss for {peer_id}: {str(e)}")

    async def get_connection_info(self, peer_id: str) -> Optional[Dict]:
        """Get information about a peer connection."""
        if peer_id not in self.peers:
            return None
        
        peer_conn = self.peers[peer_id]
        return {
            "peer_id": peer_id,
            "connected": peer_conn.connected,
            "last_seen": peer_conn.last_seen,
            "local_candidates": [
                str(c) for c in peer_conn.local_candidates
            ],
            "remote_candidates": [
                str(c) for c in peer_conn.stun_candidates
            ]
        }

    async def cleanup(self):
        """Clean up all connections."""
        for peer_id, peer_conn in list(self.peers.items()):
            await self.handle_connection_loss(peer_id)
        
        await self.ice_config.close()

