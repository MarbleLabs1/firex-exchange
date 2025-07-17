#!/usr/bin/env python3
"""
Blockchain Database Backup System

This script implements a daily backup system for the blockchain.db SQLite database.
It compresses backups into zip format and maintains a retention policy of 7 days.

Features:
- Daily backups with timestamp
- Zip compression to save space
- 7-day retention policy (configurable)
- Comprehensive logging
- Can be run as a standalone script or imported

Usage:
    python backup.py [--db-path PATH] [--backup-dir DIR] [--retention-days DAYS]

Example:
    python backup.py --db-path ./data/blockchain.db --backup-dir ./backups --retention-days 10
"""

import argparse
import datetime
import logging
import os
import shutil
import sys
import zipfile
from pathlib import Path


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('backup.log')
    ]
)
logger = logging.getLogger('blockchain_backup')


def create_backup(db_path, backup_dir, retention_days=7):
    """
    Create a compressed backup of the blockchain database and manage retention.
    
    Args:
        db_path (str): Path to the blockchain.db file
        backup_dir (str): Directory to store backups
        retention_days (int): Number of days to keep backups
        
    Returns:
        bool: True if backup was successful, False otherwise
    """
    try:
        # Ensure the database file exists
        db_path = Path(db_path)
        if not db_path.exists():
            logger.error(f"Database file not found: {db_path}")
            return False
            
        # Create backup directory if it doesn't exist
        backup_path = Path(backup_dir)
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # Generate timestamp for the backup filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"blockchain_backup_{timestamp}.zip"
        backup_file_path = backup_path / backup_filename
        
        logger.info(f"Starting backup of {db_path} to {backup_file_path}")
        
        # Create zip file with the database
        with zipfile.ZipFile(backup_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(db_path, arcname=db_path.name)
            
        # Verify the backup was created successfully
        if not backup_file_path.exists():
            logger.error("Backup file was not created successfully")
            return False
            
        backup_size = backup_file_path.stat().st_size
        logger.info(f"Backup completed successfully. Size: {backup_size/1024/1024:.2f} MB")
        
        # Apply retention policy
        apply_retention_policy(backup_path, retention_days)
        
        return True
        
    except Exception as e:
        logger.exception(f"Error during backup process: {str(e)}", exc_info=True)
        return False


def apply_retention_policy(backup_dir, retention_days):
    """
    Delete backups that are older than the specified retention period.
    
    Args:
        backup_dir (Path): Directory containing backups
        retention_days (int): Number of days to keep backups
    """
    try:
        logger.info(f"Applying retention policy: keeping last {retention_days} days of backups")
        
        # Calculate the cutoff date
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=retention_days)
        
        # Get list of backup files
        backup_files = list(backup_dir.glob("blockchain_backup_*.zip"))
        
        # Sort files by creation time
        backup_files.sort(key=lambda x: x.stat().st_ctime)
        
        # Count files to be deleted
        files_deleted = 0
        
        # Check each file against the retention policy
        for backup_file in backup_files:
            file_creation_time = datetime.datetime.fromtimestamp(backup_file.stat().st_ctime)
            
            if file_creation_time < cutoff_date:
                logger.info(f"Deleting old backup: {backup_file} (created on {file_creation_time})")
                backup_file.unlink()
                files_deleted += 1
                
        logger.info(f"Retention policy applied: {files_deleted} old backups removed")
        
    except Exception as e:
        logger.exception(f"Error applying retention policy: {str(e)}", exc_info=True)


def main():
    """
    Main function to parse arguments and execute the backup process.
    """
    parser = argparse.ArgumentParser(description='Blockchain Database Backup Tool')
    parser.add_argument('--db-path', type=str, default='blockchain.db',
                        help='Path to the blockchain database file (default: blockchain.db)')
    parser.add_argument('--backup-dir', type=str, default='backups',
                        help='Directory to store backups (default: backups)')
    parser.add_argument('--retention-days', type=int, default=7,
                        help='Number of days to keep backups (default: 7)')
    
    args = parser.parse_args()
    
    logger.info("Starting blockchain database backup process")
    success = create_backup(args.db_path, args.backup_dir, args.retention_days)
    
    if success:
        logger.info("Backup process completed successfully")
        return 0
    else:
        logger.error("Backup process failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

