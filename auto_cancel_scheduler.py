#!/usr/bin/env python3
"""
AUTOMATIC CANCELLATION SCHEDULER
================================

This module provides automatic cancellation for numbers with background verification only.
Numbers WITHOUT background verification will NEVER be automatically canceled.

Key Features:
- Only cancels numbers that have background verification flag set to True
- Numbers without background verification are completely protected
- Configurable timeout periods
- Detailed logging and statistics
- Safe cancellation with proper cleanup
"""

import threading
import time
import schedule
import logging
from datetime import datetime, timedelta
from db import (
    auto_cancel_background_verification_numbers,
    get_auto_cancellation_stats,
    get_numbers_with_background_verification,
    get_numbers_without_background_verification
)
from bot_init import bot
from config import ADMIN_IDS

# Configuration
AUTO_CANCEL_ENABLED = True
AUTO_CANCEL_TIMEOUT_MINUTES = 30  # Cancel background verifications after 30 minutes
CHECK_INTERVAL_MINUTES = 5  # Check every 5 minutes
NOTIFICATION_ENABLED = True

# Global scheduler control
scheduler_thread = None
scheduler_running = False

def setup_logging():
    """Setup logging for auto-cancellation system"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger('auto_cancel')

logger = setup_logging()

def auto_cancel_job():
    """
    Main job that runs periodically to cancel background verification numbers.
    IMPORTANT: Only cancels numbers WITH background verification.
    Numbers WITHOUT background verification are NEVER touched.
    """
    try:
        if not AUTO_CANCEL_ENABLED:
            return
        
        logger.info("🤖 Starting automatic cancellation check...")
        
        # Get statistics before cancellation
        stats_before = get_auto_cancellation_stats()
        
        # Get numbers that will be protected (no background verification)
        protected_numbers = get_numbers_without_background_verification()
        protected_count = len(protected_numbers)
        
        # Get numbers that are eligible for cancellation (with background verification)
        eligible_numbers = get_numbers_with_background_verification(AUTO_CANCEL_TIMEOUT_MINUTES)
        eligible_count = len(eligible_numbers)
        
        logger.info(f"📊 Protected numbers (no background verification): {protected_count}")
        logger.info(f"📊 Eligible for cancellation (background verification): {eligible_count}")
        
        if eligible_count == 0:
            logger.info("✅ No numbers eligible for auto-cancellation")
            return
        
        # Perform automatic cancellation (only background verification numbers)
        cancelled_count = auto_cancel_background_verification_numbers(AUTO_CANCEL_TIMEOUT_MINUTES)
        
        # Get statistics after cancellation
        stats_after = get_auto_cancellation_stats()
        
        # Log results
        if cancelled_count > 0:
            logger.info(f"🤖 Auto-cancelled {cancelled_count} background verification numbers")
            
            # Send notification to admins if enabled
            if NOTIFICATION_ENABLED and cancelled_count > 0:
                send_admin_notification(cancelled_count, stats_before, stats_after, protected_count)
        else:
            logger.info("✅ No background verification numbers were cancelled")
            
    except Exception as e:
        logger.error(f"❌ Error in auto_cancel_job: {e}")
        import traceback
        traceback.print_exc()

def send_admin_notification(cancelled_count, stats_before, stats_after, protected_count):
    """Send notification to admins about auto-cancellation results"""
    try:
        message = f"""🤖 **AUTO-CANCELLATION REPORT**

🛑 **Cancelled**: {cancelled_count} numbers with background verification
✅ **Protected**: {protected_count} numbers without background verification
⏰ **Timeout**: {AUTO_CANCEL_TIMEOUT_MINUTES} minutes

📊 **STATISTICS:**
• Background verification numbers: {stats_after.get('numbers_with_background_verification', 0)}
• Protected numbers: {stats_after.get('numbers_without_background_verification', 0)}
• Total auto-cancelled: {stats_after.get('auto_cancelled_count', 0)}

🔒 **SAFETY**: Numbers without background verification are NEVER auto-cancelled."""

        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(admin_id, message, parse_mode="Markdown")
            except Exception as send_error:
                logger.error(f"❌ Error sending notification to admin {admin_id}: {send_error}")
                
    except Exception as e:
        logger.error(f"❌ Error in send_admin_notification: {e}")

def start_auto_cancel_scheduler():
    """Start the automatic cancellation scheduler"""
    global scheduler_thread, scheduler_running
    
    if scheduler_running:
        logger.warning("⚠️ Auto-cancel scheduler is already running")
        return False
    
    try:
        # Clear any existing scheduled jobs
        schedule.clear('auto-cancel')
        
        # Schedule the auto-cancellation job
        schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(auto_cancel_job).tag('auto-cancel')
        
        def run_scheduler():
            global scheduler_running
            scheduler_running = True
            logger.info(f"🤖 Auto-cancel scheduler started (check every {CHECK_INTERVAL_MINUTES}m, timeout: {AUTO_CANCEL_TIMEOUT_MINUTES}m)")
            
            while scheduler_running:
                try:
                    schedule.run_pending()
                    time.sleep(30)  # Check every 30 seconds
                except Exception as e:
                    logger.error(f"❌ Error in scheduler loop: {e}")
                    time.sleep(60)  # Wait longer on error
            
            logger.info("🛑 Auto-cancel scheduler stopped")
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True, name="AutoCancelScheduler")
        scheduler_thread.start()
        
        # Run initial check
        threading.Thread(target=auto_cancel_job, daemon=True, name="InitialAutoCancelCheck").start()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error starting auto-cancel scheduler: {e}")
        return False

def stop_auto_cancel_scheduler():
    """Stop the automatic cancellation scheduler"""
    global scheduler_running
    
    if not scheduler_running:
        logger.warning("⚠️ Auto-cancel scheduler is not running")
        return False
    
    try:
        scheduler_running = False
        schedule.clear('auto-cancel')
        logger.info("🛑 Auto-cancel scheduler stopped")
        return True
    except Exception as e:
        logger.error(f"❌ Error stopping auto-cancel scheduler: {e}")
        return False

def get_scheduler_status():
    """Get the status of the auto-cancellation scheduler"""
    try:
        stats = get_auto_cancellation_stats()
        return {
            "enabled": AUTO_CANCEL_ENABLED,
            "running": scheduler_running,
            "timeout_minutes": AUTO_CANCEL_TIMEOUT_MINUTES,
            "check_interval_minutes": CHECK_INTERVAL_MINUTES,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"❌ Error getting scheduler status: {e}")
        return {}

def force_auto_cancel_check():
    """Force an immediate auto-cancellation check"""
    try:
        logger.info("🔧 Force running auto-cancellation check...")
        auto_cancel_job()
        return True
    except Exception as e:
        logger.error(f"❌ Error in force auto-cancel check: {e}")
        return False

def update_auto_cancel_settings(enabled=None, timeout_minutes=None, check_interval_minutes=None):
    """Update auto-cancellation settings"""
    global AUTO_CANCEL_ENABLED, AUTO_CANCEL_TIMEOUT_MINUTES, CHECK_INTERVAL_MINUTES
    
    try:
        restart_needed = False
        
        if enabled is not None:
            AUTO_CANCEL_ENABLED = enabled
            logger.info(f"🔧 Auto-cancel enabled: {enabled}")
        
        if timeout_minutes is not None:
            AUTO_CANCEL_TIMEOUT_MINUTES = timeout_minutes
            logger.info(f"🔧 Auto-cancel timeout: {timeout_minutes} minutes")
        
        if check_interval_minutes is not None:
            CHECK_INTERVAL_MINUTES = check_interval_minutes
            restart_needed = True
            logger.info(f"🔧 Auto-cancel check interval: {check_interval_minutes} minutes")
        
        if restart_needed and scheduler_running:
            stop_auto_cancel_scheduler()
            start_auto_cancel_scheduler()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error updating auto-cancel settings: {e}")
        return False

# Auto-start the scheduler when module is imported
if __name__ != "__main__":
    # Start scheduler automatically when imported
    try:
        start_auto_cancel_scheduler()
    except Exception as e:
        logger.error(f"❌ Error auto-starting scheduler: {e}")