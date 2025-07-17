import time
from typing import Dict, Optional
from loguru import logger
import json
import os
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self):
        self.rate_limits = {
            "ui_update": {"calls": 1, "period": 1},  # 1 call per second
            "order_book": {"calls": 2, "period": 1},  # 2 calls per second
            "trades": {"calls": 2, "period": 1},  # 2 calls per second
            "analytics": {"calls": 1, "period": 1},  # 1 call per second
            "place_order": {"calls": 5, "period": 60},  # 5 calls per minute
            "toggle_strategy": {"calls": 2, "period": 60},  # 2 calls per minute
        }
        self.call_history: Dict[str, list] = {}
        self.history_file = "rate_limit_history.json"
        
    def initialize(self):
        """Initialize rate limiter"""
        try:
            # Load call history
            if os.path.exists(self.history_file):
                with open(self.history_file, "r") as f:
                    self.call_history = json.load(f)
                    
            logger.info("Rate limiter initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize rate limiter: {str(e)}")
            raise
            
    def check_rate_limit(self, operation: str) -> bool:
        """Check if operation is within rate limits"""
        try:
            # Get rate limit for operation
            if operation not in self.rate_limits:
                logger.warning(f"No rate limit defined for operation: {operation}")
                return True
                
            limit = self.rate_limits[operation]
            
            # Initialize call history for operation
            if operation not in self.call_history:
                self.call_history[operation] = []
                
            # Get current time
            now = datetime.now()
            
            # Remove old calls
            self.call_history[operation] = [
                call_time for call_time in self.call_history[operation]
                if now - datetime.fromisoformat(call_time) < timedelta(seconds=limit["period"])
            ]
            
            # Check if within limit
            if len(self.call_history[operation]) >= limit["calls"]:
                logger.warning(f"Rate limit exceeded for operation: {operation}")
                return False
                
            # Add current call
            self.call_history[operation].append(now.isoformat())
            
            # Save history
            self._save_history()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to check rate limit: {str(e)}")
            return False
            
    def get_operation_stats(self, operation: str) -> Optional[Dict]:
        """Get statistics for an operation"""
        try:
            if operation not in self.call_history:
                return None
                
            now = datetime.now()
            calls = self.call_history[operation]
            
            # Filter recent calls
            recent_calls = [
                call_time for call_time in calls
                if now - datetime.fromisoformat(call_time) < timedelta(seconds=60)
            ]
            
            return {
                "total_calls": len(calls),
                "recent_calls": len(recent_calls),
                "limit": self.rate_limits.get(operation, {}).get("calls", 0),
                "period": self.rate_limits.get(operation, {}).get("period", 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get operation stats: {str(e)}")
            return None
            
    def _save_history(self):
        """Save call history to file"""
        try:
            with open(self.history_file, "w") as f:
                json.dump(self.call_history, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save call history: {str(e)}")
            raise
            
    def cleanup(self):
        """Clean up rate limiter"""
        try:
            self._save_history()
            self.call_history = {}
            logger.info("Rate limiter cleaned up successfully")
        except Exception as e:
            logger.error(f"Failed to cleanup rate limiter: {str(e)}")
            raise 