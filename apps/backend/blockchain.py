"""
apps.backend.blockchain
-----------------------
Provides Immutable Evidence Anchoring.
Uses a pure-Python mock Ethereum node to avoid C++ build dependencies on Windows.
"""

import hashlib
import json
import logging
import time
import uuid
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

class MockEthereumNode:
    """A pure-Python in-memory blockchain for hackathon demonstrations."""
    def __init__(self):
        self.transactions = {}
        self.blocks = []
        self.account = "0x" + hashlib.sha1(b"IBVAP_ADMIN").hexdigest() + "000000000000000000000000"

    def send_transaction(self, data: str) -> str:
        # Create a deterministic fake TxHash
        tx_hash = "0x" + hashlib.sha256((data + str(time.time()) + str(uuid.uuid4())).encode()).hexdigest()
        self.transactions[tx_hash] = {
            "from": self.account,
            "to": self.account,
            "data": data,
            "timestamp": time.time()
        }
        return tx_hash


class BlockchainAnchor:
    def __init__(self):
        self.node = MockEthereumNode()
        logger.info("Successfully connected to In-Memory Ethereum Node (Mock)")

    def anchor_evidence(self, incident_data: Dict[str, Any]) -> Tuple[str, str]:
        """
        Hashes the incident data and stores the hash on the blockchain.
        Returns (transaction_hash, evidence_hash)
        """
        try:
            # 1. Create a deterministic string representation of the incident
            data_string = json.dumps(incident_data, sort_keys=True)
            
            # 2. Hash it using SHA-256 (acting as the Evidence Hash)
            evidence_hash = hashlib.sha256(data_string.encode('utf-8')).hexdigest()
            hex_evidence = f"0x{evidence_hash}"

            # 3. Anchor it to the blockchain via a 0 ETH transaction
            tx_hash_str = self.node.send_transaction(hex_evidence)
            
            logger.info(f"Anchored Incident to Blockchain. TxHash: {tx_hash_str}")
            return tx_hash_str, hex_evidence

        except Exception as e:
            logger.error(f"Blockchain anchoring failed: {e}")
            return "0xError", "0xError"

# Global singleton
anchor = BlockchainAnchor()
