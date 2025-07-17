import os
import json
import hashlib
import hmac
import base64
import time
from typing import Dict, Optional, Tuple
from loguru import logger
from cryptography.fernet import Fernet

class AuthManager:
    def __init__(self):
        self.session_token = None
        self.user_data = None
        self.fernet = None
        self.key = None
        
    def initialize(self):
        """Initialize authentication manager"""
        try:
            # Load or generate encryption key
            if os.path.exists("auth.key"):
                with open("auth.key", "rb") as f:
                    self.key = f.read()
            else:
                self.key = Fernet.generate_key()
                with open("auth.key", "wb") as f:
                    f.write(self.key)
                    
            self.fernet = Fernet(self.key)
            logger.info("Authentication manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize authentication: {str(e)}")
            raise
            
    def login(self, username: str, password: str) -> bool:
        """Authenticate user and create session"""
        try:
            # Load user data
            if not os.path.exists("users.json"):
                logger.error("No users found")
                return False
                
            with open("users.json", "r") as f:
                users = json.load(f)
                
            # Check if user exists
            if username not in users:
                logger.error(f"User {username} not found")
                return False
                
            # Verify password
            stored_hash = users[username]["password_hash"]
            if not self._verify_password(password, stored_hash):
                logger.error("Invalid password")
                return False
                
            # Create session token
            self.session_token = self._generate_session_token(username)
            self.user_data = users[username]
            
            # Save session
            self._save_session()
            
            logger.info(f"User {username} logged in successfully")
            return True
            
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False
            
    def logout(self):
        """End user session"""
        try:
            if self.session_token:
                # Remove session file
                if os.path.exists("session.json"):
                    os.remove("session.json")
                    
                self.session_token = None
                self.user_data = None
                logger.info("User logged out successfully")
                
        except Exception as e:
            logger.error(f"Logout failed: {str(e)}")
            raise
            
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        try:
            if not self.session_token:
                # Try to load session
                if os.path.exists("session.json"):
                    with open("session.json", "r") as f:
                        session = json.load(f)
                        
                    # Verify session token
                    if self._verify_session_token(session["token"], session["username"]):
                        self.session_token = session["token"]
                        self.user_data = session["user_data"]
                        return True
                        
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Authentication check failed: {str(e)}")
            return False
            
    def get_user_data(self) -> Optional[Dict]:
        """Get current user data"""
        return self.user_data
        
    def _generate_session_token(self, username: str) -> str:
        """Generate a new session token"""
        try:
            # Create token data
            timestamp = str(int(time.time()))
            data = f"{username}:{timestamp}"
            
            # Generate HMAC
            h = hmac.new(self.key, data.encode(), hashlib.sha256)
            
            # Return base64 encoded token
            return base64.b64encode(h.digest()).decode()
            
        except Exception as e:
            logger.error(f"Failed to generate session token: {str(e)}")
            raise
            
    def _verify_session_token(self, token: str, username: str) -> bool:
        """Verify session token"""
        try:
            # Decode token
            token_bytes = base64.b64decode(token)
            
            # Get timestamp from session file
            with open("session.json", "r") as f:
                session = json.load(f)
                timestamp = session["timestamp"]
                
            # Create verification data
            data = f"{username}:{timestamp}"
            
            # Generate HMAC
            h = hmac.new(self.key, data.encode(), hashlib.sha256)
            
            # Compare tokens
            return hmac.compare_digest(h.digest(), token_bytes)
            
        except Exception as e:
            logger.error(f"Failed to verify session token: {str(e)}")
            return False
            
    def _verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify password against stored hash"""
        try:
            # Generate hash of provided password
            h = hashlib.sha256(password.encode())
            password_hash = base64.b64encode(h.digest()).decode()
            
            # Compare hashes
            return hmac.compare_digest(password_hash, stored_hash)
            
        except Exception as e:
            logger.error(f"Failed to verify password: {str(e)}")
            return False
            
    def _save_session(self):
        """Save session data"""
        try:
            session = {
                "token": self.session_token,
                "username": self.user_data["username"],
                "user_data": self.user_data,
                "timestamp": str(int(time.time()))
            }
            
            # Encrypt session data
            encrypted_session = self.fernet.encrypt(json.dumps(session).encode())
            
            # Save to file
            with open("session.json", "wb") as f:
                f.write(encrypted_session)
                
        except Exception as e:
            logger.error(f"Failed to save session: {str(e)}")
            raise
            
    def cleanup(self):
        """Clean up authentication resources"""
        try:
            self.session_token = None
            self.user_data = None
            self.fernet = None
            self.key = None
            logger.info("Authentication manager cleaned up successfully")
        except Exception as e:
            logger.error(f"Failed to cleanup authentication manager: {str(e)}")
            raise 