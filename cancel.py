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
        # Only show the current active number (pending_phone), not all pending numbers
        current_phone = user.get("pending_phone")
        
        if not current_phone:
            bot.reply_to(message, TRANSLATIONS['no_pending_verification'][lang])
            return
        
        # Check if this number is in database (post-OTP) or just in user record (OTP phase)
        from db import db
        pending_record = db.pending_numbers.find_one({
            "user_id": user_id, 
            "phone_number": current_phone, 
            "status": "pending"
        })
        
        # Create a single-item list with only the current active number
        if pending_record:
            # Number is in database (post-OTP phase)
            pending_numbers = [pending_record]
            print(f"🎯 Found current active number in database: {current_phone}")
        else:
            # Number is in OTP phase, create fake record for button interface
            pending_numbers = [{
                "phone_number": current_phone,
                "status": "pending", 
                "created_at": "OTP Phase",
                "_id": "otp_phase"
            }]
            print(f"🎯 Created button interface for current OTP phase number: {current_phone}")
        
        # Show the current active number as a button
        from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard = InlineKeyboardMarkup()
        # Only one number (the current active one)
        record = pending_numbers[0]
        button_text = f"📱 {record['phone_number']}"
        callback_data = f"cancel_{record['phone_number']}"
        keyboard.add(InlineKeyboardButton(button_text, callback_data=callback_data))
        
        # Add back button
        keyboard.add(InlineKeyboardButton("🔙 Back", callback_data="cancel_back"))
        
        # Create the message text
        cancel_options_msg = (
            f"📱 *Cancel Current Number*\n\n"
            f"Current active number:\n\n"
            f"👆 Click on the number to cancel it:"
        )
        
        bot.reply_to(message, cancel_options_msg, parse_mode="Markdown", reply_markup=keyboard)
        return  # Wait for user to click a button
    except Exception as e:
        bot.reply_to(message, "⚠️ An error occurred while cancelling. Please try again.")
        print(f"❌ Cancel error for user {user_id}: {e}")

# Callback handler for cancel button clicks
@bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_'))
def handle_cancel_callback(call):
    """Handle cancel button clicks"""
    try:
        user_id = call.from_user.id
        user = get_user(user_id) or {}
        lang = user.get('language', 'English')
        
        # Extract the action from callback data
        action = call.data.replace('cancel_', '')
        
        if action == 'back':
            # User clicked back, just delete the message
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.answer_callback_query(call.id, "❌ Cancelled")
            return
        

        else:
            # User clicked on a specific phone number
            phone_number = action
            
            # Check if this is an OTP phase cancellation or regular pending number
            from db import db
            pending_record = db.pending_numbers.find_one({
                "user_id": user_id, 
                "phone_number": phone_number, 
                "status": "pending"
            })
            
            # Check if this is OTP phase (no database record but user has pending_phone)
            user_data = get_user(user_id)
            is_otp_phase = not pending_record and user_data and user_data.get("pending_phone") == phone_number
            
            if not pending_record and not is_otp_phase:
                bot.answer_callback_query(call.id, "❌ This number cannot be cancelled")
                return
            
            # Perform the cancellation (different logic for OTP phase vs regular)
            if is_otp_phase:
                success = cancel_otp_phase_number(user_id, phone_number, lang)
            else:
                success = cancel_specific_number(user_id, phone_number, lang)
            
            if success:
                bot.answer_callback_query(call.id, f"✅ Cancelled {phone_number}")
                
                # Show completion message since we only had one number
                final_msg = f"✅ *Number Cancelled*\n\n📞 Cancelled: `{phone_number}`\n🔄 This number can now be used again"
                bot.edit_message_text(final_msg, call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            else:
                bot.answer_callback_query(call.id, "❌ Failed to cancel number")
    
    except Exception as e:
        bot.answer_callback_query(call.id, "⚠️ Error occurred")
        print(f"❌ Cancel callback error: {e}")

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