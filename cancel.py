import os
import asyncio
import threading
from db import get_user, update_user, unmark_number_used, delete_specific_pending_number
from utils import require_channel_membership
from bot_init import bot
from telegram_otp import session_manager
from config import SESSIONS_DIR
from translations import TRANSLATIONS

# Use the same async loop as otp.py
def run_async(coro):
    """Run async function in the background thread"""
    try:
        # Try to get the existing event loop from otp.py
        from otp import otp_loop
        future = asyncio.run_coroutine_threadsafe(coro, otp_loop)
        return future.result(timeout=10)  # 10 second timeout
    except Exception as e:
        print(f"Error running async in cancel: {e}")
        return False

@bot.message_handler(commands=['cancel'])
@require_channel_membership
def handle_cancel(message):
    """Cancel function has been disabled"""
    user_id = message.from_user.id
    user = get_user(user_id) or {}
    lang = user.get('language', 'English')
    
    # Send message that cancel function is disabled
    disabled_msg = "❌ *Cancel Function Disabled*\n\nThe cancel function has been disabled. Please wait for the verification process to complete."
    bot.reply_to(message, disabled_msg, parse_mode="Markdown")
    print(f"🚫 Cancel function disabled for user {user_id}")

# Callback handler for cancel button clicks (DISABLED)
@bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_'))
def handle_cancel_callback(call):
    """Cancel callback handler has been disabled"""
    bot.answer_callback_query(call.id, "❌ Cancel function is disabled")
    print(f"🚫 Cancel callback disabled for user {call.from_user.id}")

def cancel_otp_phase_number(user_id: int, phone_number: str, lang: str) -> bool:
    """Cancel a number that's in OTP phase (not yet in pending_numbers table)"""
    try:
        print(f"🗑️ Cancelling OTP verification for {phone_number} (User: {user_id})")
        
        # Cancel background verification
        from otp import cancel_background_verification
        background_cancelled, background_phone = cancel_background_verification(user_id)
        if background_cancelled:
            print(f"🛑 Background verification cancelled for {background_phone}")
            import time
            time.sleep(1)
        
        # Clean up session files
        session_info = session_manager.get_session_info(phone_number)
        session_path = session_info["session_path"]
        temp_session_path = session_manager.user_states.get(user_id, {}).get("session_path")
        
        for path in [session_path, temp_session_path]:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
                    print(f"✅ Removed session file: {path}")
            except Exception as e:
                print(f"Error removing session file {path}: {e}")
        
        # Clean up session manager state
        cleanup_success = run_async(session_manager.cleanup_session(user_id))
        
        # Clear user data
        update_user(user_id, {
            "pending_phone": None,
            "otp_msg_id": None,
            "country_code": None
        })
        
        # Unmark number as used
        unmark_number_used(phone_number)
        
        print(f"✅ Successfully cancelled OTP verification for {phone_number}")
        return True
        
    except Exception as e:
        print(f"❌ Error cancelling OTP phase {phone_number}: {e}")
        return False

def cancel_specific_number(user_id: int, phone_number: str, lang: str) -> bool:
    """Cancel a specific number for a user"""
    try:
        print(f"🗑️ Cancelling verification for {phone_number} (User: {user_id})")
        
        # Cancel background verification
        from otp import cancel_background_verification
        background_cancelled, background_phone = cancel_background_verification(user_id)
        if background_cancelled:
            print(f"🛑 Background verification cancelled for {background_phone}")
            import time
            time.sleep(1)
        
        # Remove from used numbers
        unmark_success = unmark_number_used(phone_number)
        if unmark_success:
            print(f"✅ Number {phone_number} unmarked (can be used again)")
        
        # Clean up session files
        session_info = session_manager.get_session_info(phone_number)
        session_path = session_info["session_path"]
        temp_session_path = session_manager.user_states.get(user_id, {}).get("session_path")
        
        for path in [session_path, temp_session_path]:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
                    print(f"✅ Removed session file: {path}")
            except Exception as e:
                print(f"Error removing session file {path}: {e}")
        
        # Clean up session manager state
        cleanup_success = run_async(session_manager.cleanup_session(user_id))
        
        # Delete specific pending number
        deleted_pending = delete_specific_pending_number(user_id, phone_number)
        if deleted_pending:
            print(f"✅ Deleted pending number record for {phone_number}")
        
        # Update user data if this was the current pending_phone
        current_user = get_user(user_id)
        if current_user and current_user.get("pending_phone") == phone_number:
            # Find other pending numbers to set as new pending_phone
            from db import db
            remaining_pending = list(db.pending_numbers.find(
                {"user_id": user_id, "status": "pending", "phone_number": {"$ne": phone_number}}
            ).sort("created_at", -1))
            
            new_pending_phone = remaining_pending[0]["phone_number"] if remaining_pending else None
            
            update_user(user_id, {
                "pending_phone": new_pending_phone,
                "otp_msg_id": None if not new_pending_phone else current_user.get("otp_msg_id"),
                "country_code": None if not new_pending_phone else current_user.get("country_code")
            })
        
        print(f"✅ Successfully cancelled verification for {phone_number}")
        return True
        
    except Exception as e:
        print(f"❌ Error cancelling {phone_number}: {e}")
        return False