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
    try:
        user_id = message.from_user.id
        user = get_user(user_id) or {}
        lang = user.get('language', 'English')
        # Find all pending numbers for this user (with status "pending")
        from db import db
        pending_numbers = list(db.pending_numbers.find(
            {"user_id": user_id, "status": "pending"}
        ).sort("created_at", -1))  # Most recent first
        
        # If no pending numbers in database, check if user has pending_phone (OTP phase)
        if not pending_numbers:
            if user.get("pending_phone"):
                # User is in OTP phase, use the pending_phone
                phone_number = user["pending_phone"]
                print(f"🎯 No pending numbers in database, but user has pending_phone: {phone_number} (OTP phase)")
                
                # Handle OTP phase cancellation
                print(f"🗑️ Cancelling OTP verification for {phone_number} (User: {user_id})")
                
                # Cancel background verification and clean up
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
                
                # Send confirmation message
                status_msg = TRANSLATIONS['verification_cancelled'][lang].format(phone=phone_number)
                bot.reply_to(message, status_msg, parse_mode="Markdown")
                print(f"✅ Successfully cancelled OTP verification for {phone_number}")
                return
            else:
                bot.reply_to(message, TRANSLATIONS['no_pending_verification'][lang])
                return
        
        # If user has multiple pending numbers, show them and ask which to cancel
        if len(pending_numbers) > 1:
            numbers_list = []
            for i, record in enumerate(pending_numbers, 1):
                numbers_list.append(f"{i}. `{record['phone_number']}` - {record.get('created_at', 'Unknown time')}")
            
            cancel_options_msg = (
                f"📱 *Multiple Numbers Found*\n\n"
                f"You have {len(pending_numbers)} numbers that can be cancelled:\n\n" +
                "\n".join(numbers_list) + "\n\n"
                f"💡 Cancelling the most recent number: `{pending_numbers[0]['phone_number']}`"
            )
            bot.reply_to(message, cancel_options_msg, parse_mode="Markdown")
        
        # Use the most recent pending number (first in the sorted list)
        most_recent = pending_numbers[0]
        phone_number = most_recent["phone_number"]
        pending_id = str(most_recent["_id"])
        
        print(f"🎯 Found {len(pending_numbers)} pending numbers for user {user_id}, cancelling most recent: {phone_number}")
        
        # Since we already filtered by status "pending", we know this number can be cancelled
        # But let's double-check the current status in case it changed
        current_status = most_recent.get("status")
        if current_status != "pending":
            print(f"🚫 Cancel blocked - Number {phone_number} status changed to '{current_status}' during processing")
            bot.reply_to(message, TRANSLATIONS['cannot_cancel_received'][lang], parse_mode="Markdown")
            return
        
        print(f"🗑️ Cancelling verification for {phone_number} (User: {user_id})")
        # 0. Cancel any running background verification thread
        from otp import cancel_background_verification
        background_cancelled, background_phone = cancel_background_verification(user_id)
        if background_cancelled:
            print(f"🛑 Background verification cancelled for {background_phone}")
            import time
            time.sleep(1)
        else:
            print(f"ℹ️ No active background verification found for user {user_id}")
        # 1. Remove number from used_numbers (so it can be used again)
        unmark_success = unmark_number_used(phone_number)
        if unmark_success:
            print(f"✅ Number {phone_number} unmarked (can be used again)")
        else:
            print(f"⚠️ Number {phone_number} was not marked as used or failed to unmark")
        # 2. Clean up session files from server (including country-specific folders)
        session_info = session_manager.get_session_info(phone_number)
        session_path = session_info["session_path"]
        temp_session_path = session_manager.user_states.get(user_id, {}).get("session_path")
        removed_files = 0
        for path in [session_path, temp_session_path]:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
                    removed_files += 1
                    print(f"✅ Removed session file: {path}")
            except Exception as e:
                print(f"Error removing session file {path}: {e}")
        legacy_session_path = os.path.join(SESSIONS_DIR, f"{phone_number}.session")
        if os.path.exists(legacy_session_path):
            try:
                os.remove(legacy_session_path)
                removed_files += 1
                print(f"✅ Removed legacy session file: {legacy_session_path}")
            except Exception as e:
                print(f"Error removing legacy session file {legacy_session_path}: {e}")
        # 3. Clean up the session manager state and disconnect client
        cleanup_success = run_async(session_manager.cleanup_session(user_id))
        # 4. Delete only the specific pending number being cancelled
        deleted_pending = delete_specific_pending_number(user_id, phone_number)
        if deleted_pending:
            print(f"✅ Deleted pending number record for {phone_number} (User: {user_id})")
        else:
            print(f"⚠️ No pending number record found for {phone_number} (User: {user_id})")
        # 5. Update user in database (clear verification data only for this specific number)
        current_user = get_user(user_id)
        if current_user and current_user.get("pending_phone") == phone_number:
            # This was the current pending phone, clear it
            # Check if user has other pending numbers to set as new pending_phone
            remaining_pending = list(db.pending_numbers.find(
                {"user_id": user_id, "status": "pending", "phone_number": {"$ne": phone_number}}
            ).sort("created_at", -1))
            
            new_pending_phone = remaining_pending[0]["phone_number"] if remaining_pending else None
            
            update_success = update_user(user_id, {
                "pending_phone": new_pending_phone,
                "otp_msg_id": None if not new_pending_phone else current_user.get("otp_msg_id"),
                "country_code": None if not new_pending_phone else current_user.get("country_code")
            })
            
            if new_pending_phone:
                print(f"✅ Set new pending_phone to {new_pending_phone} for user {user_id}")
            else:
                print(f"✅ Cleared pending_phone for user {user_id} (no more pending numbers)")
        else:
            print(f"ℹ️ User's pending_phone ({current_user.get('pending_phone') if current_user else 'None'}) doesn't match cancelled number ({phone_number}), no user data update needed")
            update_success = True  # Don't update if it's not the current pending number
        if update_success:
            print(f"✅ User {user_id} verification data cleared")
        # Send confirmation message (translated)
        status_msg = TRANSLATIONS['verification_cancelled'][lang].format(phone=phone_number)
        bot.reply_to(message, status_msg, parse_mode="Markdown")
        print(f"✅ Successfully cancelled verification for {phone_number}")
    except Exception as e:
        bot.reply_to(message, "⚠️ An error occurred while cancelling. Please try again.")
        print(f"❌ Cancel error for user {user_id}: {e}")