import sys
import traceback
from typing import Optional, Dict, Any
from loguru import logger
import json
import os
from datetime import datetime

class ErrorHandler:
    def __init__(self):
        self.error_log = []
        self.max_errors = 1000
        self.error_file = "error_log.json"
        
    def initialize(self):
        """Initialize error handler"""
        try:
            # Load existing error log
            if os.path.exists(self.error_file):
                with open(self.error_file, "r") as f:
                    self.error_log = json.load(f)
                    
            # Set up error logging
            logger.add(
                "error.log",
                rotation="1 day",
                retention="7 days",
                level="ERROR",
                format="{time} {level} {message}"
            )
            
            logger.info("Error handler initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize error handler: {str(e)}")
            raise
            
    def handle_error(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Handle an error"""
        try:
            # Get error details
            error_type = type(error).__name__
            error_message = str(error)
            stack_trace = traceback.format_exc()
            
            # Create error entry
            error_entry = {
                "timestamp": datetime.now().isoformat(),
                "type": error_type,
                "message": error_message,
                "stack_trace": stack_trace,
                "context": context or {}
            }
            
            # Add to error log
            self.error_log.append(error_entry)
            
            # Trim log if too long
            if len(self.error_log) > self.max_errors:
                self.error_log = self.error_log[-self.max_errors:]
                
            # Save error log
            self._save_error_log()
            
            # Log error
            logger.error(f"Error: {error_type} - {error_message}")
            logger.error(f"Stack trace: {stack_trace}")
            if context:
                logger.error(f"Context: {context}")
                
        except Exception as e:
            logger.error(f"Failed to handle error: {str(e)}")
            raise
            
    def get_error_log(self) -> list:
        """Get error log"""
        return self.error_log
        
    def clear_error_log(self):
        """Clear error log"""
        try:
            self.error_log = []
            self._save_error_log()
            logger.info("Error log cleared")
        except Exception as e:
            logger.error(f"Failed to clear error log: {str(e)}")
            raise
            
    def _save_error_log(self):
        """Save error log to file"""
        try:
            with open(self.error_file, "w") as f:
                json.dump(self.error_log, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save error log: {str(e)}")
            raise
            
    def get_error_summary(self) -> Dict[str, Any]:
        """Get error summary statistics"""
        try:
            if not self.error_log:
                return {
                    "total_errors": 0,
                    "error_types": {},
                    "recent_errors": []
                }
                
            # Count error types
            error_types = {}
            for error in self.error_log:
                error_type = error["type"]
                error_types[error_type] = error_types.get(error_type, 0) + 1
                
            # Get recent errors
            recent_errors = self.error_log[-5:]  # Last 5 errors
            
            return {
                "total_errors": len(self.error_log),
                "error_types": error_types,
                "recent_errors": recent_errors
            }
            
        except Exception as e:
            logger.error(f"Failed to get error summary: {str(e)}")
            raise
            
    def cleanup(self):
        """Clean up error handler"""
        try:
            self._save_error_log()
            self.error_log = []
            logger.info("Error handler cleaned up successfully")
        except Exception as e:
            logger.error(f"Failed to cleanup error handler: {str(e)}")
            raise 