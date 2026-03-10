import hashlib
import json
import os
from time import time


class Block:
    def __init__(self, index, timestamp, data, previous_hash):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.hash = self.compute_hash()

    def compute_hash(self):
        block_string = json.dumps(
            {
                "index": self.index,
                "timestamp": self.timestamp,
                "data": self.data,
                "previous_hash": self.previous_hash,
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(block_string.encode()).hexdigest()

    def to_dict(self):
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "hash": self.hash,
        }


class Blockchain:
    def __init__(self, file_path="blockchain_data.json"):
        self.file_path = file_path
        self.chain = []
        self.load_chain()

    def create_genesis_block(self):
        genesis_block = Block(0, time(), {"message": "Genesis Block"}, "0")
        self.chain = [genesis_block]
        self.save_chain()

    def add_block(self, data):
        if not self.chain:
            self.create_genesis_block()

        previous_block = self.chain[-1]
        new_block = Block(
            index=len(self.chain),
            timestamp=time(),
            data=data,
            previous_hash=previous_block.hash,
        )
        self.chain.append(new_block)
        self.save_chain()

    def is_chain_valid(self):
        if not self.chain:
            return True

        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]

            if current_block.hash != current_block.compute_hash():
                return False

            if current_block.previous_hash != previous_block.hash:
                return False

        return True

    def get_chain(self):
        return [block.to_dict() for block in self.chain]

    def save_chain(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.get_chain(), f, indent=4)

    def load_chain(self):
        if not os.path.exists(self.file_path):
            self.create_genesis_block()
            return

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.chain = []
            for item in data:
                block = Block(
                    index=item["index"],
                    timestamp=item["timestamp"],
                    data=item["data"],
                    previous_hash=item["previous_hash"],
                )
                block.hash = item["hash"]
                self.chain.append(block)

            if not self.is_chain_valid():
                self.create_genesis_block()

        except Exception:
            self.create_genesis_block()
