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
        from otp import otp_loop
        future = asyncio.run_coroutine_threadsafe(coro, otp_loop)
        return future.result(timeout=10)
    except Exception as e:
        print(f"Error running async in cancel: {e}")
        return False

@bot.message_handler(commands=['cancel'])
@require_channel_membership
def handle_cancel(message):
    """Simple cancel function - only allows canceling pending and failed numbers"""
    try:
        user_id = message.from_user.id
        user = get_user(user_id) or {}
        lang = user.get('language', 'English')
        
        current_phone = user.get("pending_phone")
        
        if not current_phone:
            bot.reply_to(message, TRANSLATIONS['no_pending_verification'][lang])
            return
        
        # Check if this number is in database and what status it has
        from db import db
        pending_record = db.pending_numbers.find_one({
            "user_id": user_id, 
            "phone_number": current_phone
        })
        
        # Simple status check - only allow cancellation for pending and failed
        if pending_record:
            status = pending_record.get("status", "pending")
            print(f"📋 Number {current_phone} has status: {status}")
            
            # Allow cancellation only for pending and failed numbers
            if status in ["waiting", "success", "completed"]:
                # Cannot cancel numbers that are waiting for verification or already successful
                bot.reply_to(message, TRANSLATIONS['cannot_cancel_received'][lang], parse_mode="Markdown")
                print(f"🚫 Cancel blocked - Number {current_phone} has status '{status}' (cannot cancel)")
                return
        
        # Proceed with cancellation for pending/failed numbers or OTP phase
        perform_cancellation(user_id, current_phone, lang)
        
    except Exception as e:
        bot.reply_to(message, "⚠️ An error occurred while cancelling. Please try again.")
        print(f"❌ Cancel error for user {user_id}: {e}")

def perform_cancellation(user_id, phone_number, lang):
    """Perform the actual cancellation process"""
    try:
        print(f"🗑️ Starting cancellation for user {user_id}, phone {phone_number}")
        
        # Check if there's a background thread to cancel
        from otp import background_threads, thread_lock
        
        cancelled_thread = False
        with thread_lock:
            if user_id in background_threads:
                thread_info = background_threads[user_id]
                cancel_event = thread_info.get("cancel_event")
                if cancel_event:
                    cancel_event.set()
                    print(f"🛑 Signaled background thread cancellation for user {user_id}")
                    cancelled_thread = True
                
                # Remove from tracking
                del background_threads[user_id]
        
        # Clean up database records
        from db import db
        
        # Remove pending number record
        delete_result = db.pending_numbers.delete_many({
            "user_id": user_id,
            "phone_number": phone_number
        })
        print(f"🗑️ Deleted {delete_result.deleted_count} pending number records")
        
        # Clean up user state
        try:
            run_async(session_manager.cleanup_session(user_id))
            print(f"🧹 Cleaned up session for user {user_id}")
        except Exception as cleanup_error:
            print(f"⚠️ Session cleanup warning: {cleanup_error}")
        
        # Unmark the number as used (make it available again)
        unmark_result = unmark_number_used(phone_number)
        if unmark_result:
            print(f"♻️ Number {phone_number} marked as available again")
        
        # Clear user's pending phone
        update_user(user_id, {
            "pending_phone": None,
            "otp_msg_id": None
        })
        
        # Send success message
        success_messages = {
            'English': f"✅ **Cancelled Successfully**\n\n📞 Number: `{phone_number}`\n🔄 Number is now available for retry",
            'Arabic': f"✅ **تم الإلغاء بنجاح**\n\n📞 الرقم: `{phone_number}`\n🔄 الرقم متاح الآن للمحاولة مرة أخرى",
            'Chinese': f"✅ **取消成功**\n\n📞 号码: `{phone_number}`\n🔄 号码现在可以重试"
        }
        
        success_msg = success_messages.get(lang, success_messages['English'])
        bot.send_message(user_id, success_msg, parse_mode="Markdown")
        
        print(f"✅ Cancellation completed successfully for user {user_id}")
        
    except Exception as e:
        print(f"❌ Error during cancellation: {e}")
        bot.send_message(user_id, "⚠️ Cancellation partially completed. Please check your status.")

# Simple callback handler (keeping for compatibility)
@bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_'))
def handle_cancel_callback(call):
    """Handle cancel button clicks - simplified version"""
    try:
        user_id = call.from_user.id
        user = get_user(user_id) or {}
        lang = user.get('language', 'English')
        
        if call.data == "cancel_back":
            bot.delete_message(call.message.chat.id, call.message.message_id)
            return
        
        # Extract phone number from callback data
        phone_number = call.data.replace("cancel_", "")
        
        if phone_number == "otp_phase":
            # Handle OTP phase cancellation
            current_phone = user.get("pending_phone")
            if current_phone:
                perform_cancellation(user_id, current_phone, lang)
        else:
            # Handle database record cancellation
            perform_cancellation(user_id, phone_number, lang)
        
        # Delete the callback message
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
            
    except Exception as e:
        print(f"❌ Cancel callback error: {e}")
        bot.answer_callback_query(call.id, "❌ Error occurred during cancellation")