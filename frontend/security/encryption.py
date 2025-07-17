import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Dict, Any, Union
import json
from loguru import logger

class EncryptionManager:
    def __init__(self):
        self.fernet = None
        self.key = None
        self.salt = None
        
    def initialize(self):
        """Initialize encryption with a new key or load existing key"""
        try:
            # Check if key file exists
            if os.path.exists("encryption.key"):
                self._load_key()
            else:
                self._generate_key()
                
            # Initialize Fernet with the key
            self.fernet = Fernet(self.key)
            logger.info("Encryption manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {str(e)}")
            raise
            
    def _generate_key(self):
        """Generate a new encryption key"""
        try:
            # Generate a random salt
            self.salt = os.urandom(16)
            
            # Generate a key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self.salt,
                iterations=100000,
            )
            
            # Generate a random password
            password = os.urandom(32)
            
            # Derive the key
            self.key = base64.urlsafe_b64encode(kdf.derive(password))
            
            # Save the key and salt
            with open("encryption.key", "wb") as f:
                f.write(self.key)
                
            with open("encryption.salt", "wb") as f:
                f.write(self.salt)
                
        except Exception as e:
            logger.error(f"Failed to generate encryption key: {str(e)}")
            raise
            
    def _load_key(self):
        """Load existing encryption key"""
        try:
            with open("encryption.key", "rb") as f:
                self.key = f.read()
                
            with open("encryption.salt", "rb") as f:
                self.salt = f.read()
                
        except Exception as e:
            logger.error(f"Failed to load encryption key: {str(e)}")
            raise
            
    def encrypt(self, data: Union[Dict[str, Any], str]) -> str:
        """Encrypt data"""
        try:
            # Convert dict to string if necessary
            if isinstance(data, dict):
                data = json.dumps(data)
                
            # Encrypt the data
            encrypted_data = self.fernet.encrypt(data.encode())
            
            # Return base64 encoded string
            return base64.b64encode(encrypted_data).decode()
            
        except Exception as e:
            logger.error(f"Failed to encrypt data: {str(e)}")
            raise
            
    def decrypt(self, encrypted_data: str) -> Union[Dict[str, Any], str]:
        """Decrypt data"""
        try:
            # Decode base64
            encrypted_bytes = base64.b64decode(encrypted_data)
            
            # Decrypt the data
            decrypted_data = self.fernet.decrypt(encrypted_bytes)
            
            # Try to parse as JSON
            try:
                return json.loads(decrypted_data.decode())
            except json.JSONDecodeError:
                return decrypted_data.decode()
                
        except Exception as e:
            logger.error(f"Failed to decrypt data: {str(e)}")
            raise
            
    def cleanup(self):
        """Clean up encryption resources"""
        try:
            self.fernet = None
            self.key = None
            self.salt = None
            logger.info("Encryption manager cleaned up successfully")
        except Exception as e:
            logger.error(f"Failed to cleanup encryption manager: {str(e)}")
            raise 