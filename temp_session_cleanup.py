#!/usr/bin/env python3

import threading
import time
import logging
from telegram_otp import session_manager

class TempSessionCleanupScheduler:
    def __init__(self, cleanup_interval_minutes=1, max_age_minutes=2):
        """
        Initialize the cleanup scheduler
        
        Args:
            cleanup_interval_minutes: How often to run cleanup (default: 1 minute)
            max_age_minutes: Max age for temp sessions before cleanup (default: 2 minutes)
        """
        self.cleanup_interval = cleanup_interval_minutes * 60  # Convert to seconds
        self.max_age_minutes = max_age_minutes
        self.running = False
        self.thread = None
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def start(self):
        """Start the background cleanup scheduler"""
        if self.running:
            self.logger.warning("Cleanup scheduler is already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.thread.start()
        self.logger.info(f"🧹 Started temporary session cleanup scheduler (interval: {self.cleanup_interval//60}m, max_age: {self.max_age_minutes}m)")
    
    def stop(self):
        """Stop the background cleanup scheduler"""
        if not self.running:
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        self.logger.info("🛑 Stopped temporary session cleanup scheduler")
    
    def _cleanup_loop(self):
        """Main cleanup loop that runs in background thread"""
        while self.running:
            try:
                # Clean up expired user states and their temp files
                expired_states = session_manager.cleanup_expired_user_states()
                
                # Clean up orphaned temporary session files
                cleanup_count, cleanup_size = session_manager.cleanup_temporary_sessions(self.max_age_minutes)
                
                if expired_states > 0 or cleanup_count > 0:
                    self.logger.info(f"🧹 Cleanup completed: {expired_states} expired states, {cleanup_count} temp files ({cleanup_size:,} bytes)")
                
            except Exception as e:
                self.logger.error(f"❌ Error during temporary session cleanup: {e}")
            
            # Wait for next cleanup cycle
            time.sleep(self.cleanup_interval)
    
    def force_cleanup(self):
        """Force an immediate cleanup (useful for testing)"""
        try:
            self.logger.info("🧹 Force cleanup triggered...")
            expired_states = session_manager.cleanup_expired_user_states()
            cleanup_count, cleanup_size = session_manager.cleanup_temporary_sessions(self.max_age_minutes)
            self.logger.info(f"✅ Force cleanup completed: {expired_states} expired states, {cleanup_count} temp files ({cleanup_size:,} bytes)")
            return expired_states, cleanup_count, cleanup_size
        except Exception as e:
            self.logger.error(f"❌ Error during force cleanup: {e}")
            return 0, 0, 0


# Global cleanup scheduler instance
cleanup_scheduler = TempSessionCleanupScheduler(
    cleanup_interval_minutes=1,  # Run every 1 minute
    max_age_minutes=2           # Clean files older than 2 minutes
)

def start_cleanup_scheduler():
    """Start the global cleanup scheduler"""
    cleanup_scheduler.start()

def stop_cleanup_scheduler():
    """Stop the global cleanup scheduler"""
    cleanup_scheduler.stop()

def force_cleanup():
    """Force immediate cleanup"""
    return cleanup_scheduler.force_cleanup()