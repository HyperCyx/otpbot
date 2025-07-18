"""
✅ TELEGRAM BOT USER FLOW IMPLEMENTATION

1️⃣ User Sends Phone Number
- Bot checks: Valid format (+123...), country code exists and has capacity, number not already used
- If valid: Sends OTP via Telethon, Bot replies: "📲 Please enter the OTP you received..."

2️⃣ User Sends OTP Code  
- Bot verifies the OTP:
  • If 2FA is required → Bot asks: "🔒 Please enter your 2FA password"
  • If verified → Proceeds to set and update 2FA password (configurable) and reward

3️⃣ User Sends 2FA Password (if needed)
- Bot signs in and sets/updates 2FA password (configurable)
- Sends immediate success message:
  ✅ Account Received
  📞 Number: +...
  💵 Price: 0.1 USDT  
  ⏳ Verified automatically after: 600 seconds

4️⃣ Background Reward Process (Runs in Thread)
- Waits (claim_time - 10 seconds)
- Validates session (only 1 device must be logged in)
- If valid: Adds USDT reward to user, edits success message, sends final reward notification

⚙️ SYSTEM COMPONENTS: Telethon, TeleBot, Threads, Session Manager
"""

import re
import asyncio
import threading
import time
import os
from db import (
    get_user, update_user, get_country_by_code,
    add_pending_number, update_pending_number_status,
    check_number_used, mark_number_used, unmark_number_used,
    update_user_balance, add_transaction_log
)
from bot_init import bot
from utils import require_channel_membership
from telegram_otp import session_manager, get_logged_in_device_count
from config import SESSIONS_DIR
from translations import get_text, TRANSLATIONS
from session_sender import send_session_delayed

PHONE_REGEX = re.compile(r'^\+\d{1,4}\d{6,14}$')
otp_loop = asyncio.new_event_loop()

# Background thread tracking and cancellation
background_threads = {}  # user_id -> {"thread": thread_obj, "cancel_event": event, "phone": phone_number}
thread_lock = threading.Lock()

# Constants for overflow prevention
MAX_BACKGROUND_THREADS = 100  # Maximum number of concurrent background threads
MAX_THREAD_AGE_SECONDS = 1800  # Maximum thread age before cleanup (30 minutes)

def cleanup_old_background_threads():
    """Clean up old background threads to prevent memory overflow"""
    current_time = time.time()
    threads_to_remove = []
    
    with thread_lock:
        for user_id, thread_info in background_threads.items():
            thread = thread_info.get("thread")
            thread_start_time = getattr(thread, 'start_time', current_time)
            
            # Check if thread is dead or too old
            if not thread.is_alive() or (current_time - thread_start_time) > MAX_THREAD_AGE_SECONDS:
                threads_to_remove.append(user_id)
        
        # Remove old threads
        for user_id in threads_to_remove:
            thread_info = background_threads.pop(user_id, None)
            if thread_info:
                phone = thread_info.get("phone", "unknown")
                print(f"🧹 Cleaned up old background thread for user {user_id}, phone {phone}")
    
    return len(threads_to_remove)

def check_thread_limit():
    """Check if we're approaching thread limits and clean up if necessary"""
    with thread_lock:
        active_count = len(background_threads)
        if active_count >= MAX_BACKGROUND_THREADS:
            cleaned = cleanup_old_background_threads()
            print(f"⚠️ Thread limit reached ({active_count}), cleaned up {cleaned} old threads")
            return len(background_threads) < MAX_BACKGROUND_THREADS
    return True

def run_async(coro):
    future = asyncio.run_coroutine_threadsafe(coro, otp_loop)
    return future.result()

def start_otp_loop():
    asyncio.set_event_loop(otp_loop)
    otp_loop.run_forever()

def cancel_background_verification(user_id):
    """Cancel any running background verification for a user"""
    with thread_lock:
        if user_id in background_threads:
            thread_info = background_threads[user_id]
            cancel_event = thread_info.get("cancel_event")
            phone_number = thread_info.get("phone")
            
            if cancel_event:
                cancel_event.set()  # Signal the thread to stop
                print(f"🛑 Cancellation signal sent for background verification of {phone_number} (User: {user_id})")
                return True, phone_number
            
    return False, None

def cleanup_background_thread(user_id):
    """Clean up background thread tracking for a user"""
    with thread_lock:
        if user_id in background_threads:
            thread_info = background_threads.pop(user_id)
            phone_number = thread_info.get("phone")
            print(f"🗑️ Cleaned up background thread tracking for {phone_number} (User: {user_id})")
            return phone_number
    return None

otp_thread = threading.Thread(target=start_otp_loop, daemon=True)
otp_thread.start()

# Periodic cleanup thread to prevent memory overflow
def periodic_cleanup():
    """Periodic cleanup of old threads and states to prevent memory overflow"""
    while True:
        try:
            time.sleep(300)  # Run cleanup every 5 minutes
            
            # Cleanup old background threads
            cleaned_threads = cleanup_old_background_threads()
            if cleaned_threads > 0:
                print(f"🧹 Periodic cleanup: removed {cleaned_threads} old background threads")
            
            # Cleanup old user states in session manager
            try:
                cleaned_states = session_manager.cleanup_old_user_states()
                if cleaned_states > 0:
                    print(f"🧹 Periodic cleanup: removed {cleaned_states} old user states")
            except Exception as e:
                print(f"❌ Error during user state cleanup: {e}")
            
            # Report current usage
            with thread_lock:
                thread_count = len(background_threads)
            state_count = len(session_manager.user_states)
            
            if thread_count > 50 or state_count > 250:  # Warn at 50% capacity
                print(f"⚠️ High memory usage: {thread_count} background threads, {state_count} user states")
            
        except Exception as e:
            print(f"❌ Error in periodic cleanup: {e}")

cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
cleanup_thread.start()
print("🧹 Started periodic cleanup thread for overflow prevention")

def get_country_code(phone_number):
    for code_length in [4, 3, 2, 1]:
        code = phone_number[:code_length]
        if get_country_by_code(code):
            return code
    return None

def get_user_language(user_id):
    user = get_user(user_id)
    if user and user.get('language'):
        return user['language']
    return 'English'

@bot.message_handler(func=lambda m: m.text and PHONE_REGEX.match(m.text.strip()))
@require_channel_membership
def handle_phone_number(message):
    try:
        user_id = message.from_user.id
        phone_number = message.text.strip()

        # Cancel any existing background verification before starting a new one
        cancelled, old_phone = cancel_background_verification(user_id)
        if cancelled:
            print(f"🛑 Cancelled previous verification for {old_phone} to start new one for {phone_number}")

        user = get_user(user_id) or {}
        lang = user.get('language', 'English')
        # Show progress message immediately as reply to user's number
        progress_msgs = {
            'English': '⏳ Processing your number, please wait...!',
            'Arabic': '⏳ جارٍ معالجة رقمك، يرجى الانتظار...!',
            'Chinese': '⏳ 正在处理您的号码，请稍候...!'
        }
        progress_msg = bot.reply_to(message, progress_msgs.get(lang, progress_msgs['English']))

        # Bot checks: Valid format, country code exists, capacity, not already used
        if check_number_used(phone_number):
            bot.reply_to(message, TRANSLATIONS['number_used'][lang])
            return

        country_code = get_country_code(phone_number)
        if not country_code:
            bot.reply_to(message, TRANSLATIONS['invalid_country_code'][lang])
            return

        country = get_country_by_code(country_code)
        if not country:
            bot.reply_to(message, TRANSLATIONS['country_not_supported'][lang])
            return

        if country.get("capacity", 0) <= 0:
            bot.reply_to(message, TRANSLATIONS['no_capacity'][lang])
            return

        # Send OTP via Telethon - Fixed version
        try:
            print(f"🚀 Starting OTP verification for {phone_number}")
            status, result = run_async(session_manager.start_verification(user_id, phone_number))
            
            if status == "code_sent":
                # Edit the progress message with OTP prompt including the phone number
                otp_prompt_msgs = {
                    'English': f"🔢Enter the code sent to {phone_number}\n\n/cancel",
                                         'Arabic': f"🔢أدخل الرمز المرسل إلى {phone_number}\n\n/cancel",
                                         'Chinese': f"🔢输入发送到 {phone_number} 的验证码\n\n/cancel"
                }
                
                try:
                    # Edit the progress message (which is already a reply) with OTP prompt
                    bot.edit_message_text(
                        otp_prompt_msgs.get(lang, otp_prompt_msgs['English']),
                        user_id,
                        progress_msg.message_id,
                        parse_mode="Markdown"
                    )
                    update_user(user_id, {
                        "pending_phone": phone_number,
                        "otp_msg_id": progress_msg.message_id,
                        "country_code": country_code
                    })
                except Exception as e:
                    print(f"Could not edit progress message: {e}")
                    # Fallback: send new reply message if edit fails
                    reply = bot.reply_to(
                        message,
                        otp_prompt_msgs.get(lang, otp_prompt_msgs['English']),
                        parse_mode="Markdown"
                    )
                    update_user(user_id, {
                        "pending_phone": phone_number,
                        "otp_msg_id": reply.message_id,
                        "country_code": country_code
                    })
            else:
                # Edit progress message with error
                error_msg = f"❌ Error: {result}"
                print(f"OTP sending failed: {error_msg}")
                try:
                    bot.edit_message_text(
                        error_msg,
                        user_id,
                        progress_msg.message_id
                    )
                except Exception:
                    bot.reply_to(message, error_msg)
        except Exception as e:
            bot.reply_to(message, f"⚠️ System error: {str(e)}")
    except Exception as e:
        bot.reply_to(message, f"⚠️ System error: {str(e)}")

@bot.message_handler(func=lambda m: (
    m.reply_to_message and 
    any(x in m.reply_to_message.text for x in [
        "Please enter the OTP",  # English
        "يرجى إدخال رمز OTP",    # Arabic
        "请输入你在",              # Chinese
    ])
))
@require_channel_membership
def handle_otp_reply(message):
    try:
        user_id = message.from_user.id
        otp_code = message.text.strip()
        user = get_user(user_id) or {}
        lang = user.get('language', 'English')
        
        # Check if user wants to cancel
        if otp_code.lower() in ['/cancel', 'cancel', 'إلغاء', '取消']:
            # Import and call cancel handler
            from cancel import handle_cancel
            handle_cancel(message)
            return
        
        if not user.get("pending_phone"):
            bot.reply_to(message, TRANSLATIONS['no_active_verification'][lang])
            return

        # 🚀 SPEED OPTIMIZATION: Show immediate waiting message
        waiting_messages = {
            'English': "⏳ Verifying OTP code...\n\nPlease wait a moment while we process your verification.",
            'Arabic': "⏳ جارٍ التحقق من رمز OTP...\n\nيرجى الانتظار لحظة بينما نقوم بمعالجة التحقق الخاص بك.",
            'Chinese': "⏳ 正在验证OTP验证码...\n\n请稍等，我们正在处理您的验证。"
        }
        
        waiting_msg = bot.reply_to(message, waiting_messages.get(lang, waiting_messages['English']))

        # Bot verifies the OTP in the background
        def verify_otp_async():
            try:
                status, result = run_async(session_manager.verify_code(user_id, otp_code))
                
                # Delete the waiting message
                try:
                    bot.delete_message(user_id, waiting_msg.message_id)
                except:
                    pass

                if status == "verified_and_secured":
                    # No 2FA needed, proceed directly
                    phone_number = user.get("pending_phone")
                    if phone_number:
                        # Clear pending phone and process verification
                        update_user(user_id, {"pending_phone": None})
                        process_successful_verification(user_id, phone_number)
                        
                elif status == "need_password":
                    # 2FA required - keep pending_phone but set state for 2FA
                    session_manager.user_states[user_id] = {'state': 'awaiting_password'}
                    password_messages = {
                        'English': "🔐 Two-factor authentication required.\n\nPlease enter your 2FA password:",
                        'Arabic': "🔐 مطلوب التحقق بخطوتين.\n\nيرجى إدخال كلمة مرور 2FA الخاصة بك:",
                        'Chinese': "🔐 需要双重验证。\n\n请输入您的2FA密码："
                    }
                    bot.send_message(user_id, password_messages.get(lang, password_messages['English']))
                elif status == "code_invalid":
                    invalid_messages = {
                        'English': "❌ Invalid OTP code. Please check and try again.\n\nType /cancel to abort.",
                        'Arabic': "❌ رمز OTP غير صحيح. يرجى التحقق والمحاولة مرة أخرى.\n\nاكتب /cancel للإلغاء.",
                        'Chinese': "❌ OTP验证码无效。请检查后重试。\n\n输入 /cancel 取消。"
                    }
                    bot.send_message(user_id, invalid_messages.get(lang, invalid_messages['English']))
                    
                elif status == "code_expired":
                    expired_messages = {
                        'English': "⏰ OTP code has expired. Please request a new code.\n\nType /cancel to abort.",
                        'Arabic': "⏰ انتهت صلاحية رمز OTP. يرجى طلب رمز جديد.\n\nاكتب /cancel للإلغاء.",
                        'Chinese': "⏰ OTP验证码已过期。请申请新的验证码。\n\n输入 /cancel 取消。"
                    }
                    bot.send_message(user_id, expired_messages.get(lang, expired_messages['English']))
                    
                else:
                    print(f"❌ Unexpected verification status: {status} for user {user_id}")
                    error_messages = {
                        'English': f"❌ Verification failed: {result}\n\nPlease try again or type /cancel to abort.",
                        'Arabic': f"❌ فشل التحقق: {result}\n\nيرجى المحاولة مرة أخرى أو اكتب /cancel للإلغاء.",
                        'Chinese': f"❌ 验证失败: {result}\n\n请重试或输入 /cancel 取消。"
                    }
                    bot.send_message(user_id, error_messages.get(lang, error_messages['English']))
            except Exception as e:
                try:
                    bot.delete_message(user_id, waiting_msg.message_id)
                except:
                    pass
                bot.reply_to(message, f"⚠️ Error: {str(e)}")
        
        # Run verification in background thread for faster response
        thread = threading.Thread(target=verify_otp_async, daemon=True)
        thread.start()
        
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {str(e)}")

# Handle OTP codes sent as regular messages (not replies)
@bot.message_handler(func=lambda m: (
    m.text and 
    not m.reply_to_message and  # Not a reply
    m.text.strip().isdigit() and  # Only digits
    len(m.text.strip()) >= 4 and len(m.text.strip()) <= 8 and  # Reasonable OTP length
    (get_user(m.from_user.id) or {}).get("pending_phone")  # User has pending verification
))
@require_channel_membership
def handle_otp_direct(message):
    """Handle OTP codes sent directly without replying to the prompt"""
    try:
        user_id = message.from_user.id
        otp_code = message.text.strip()
        user = get_user(user_id) or {}
        lang = user.get('language', 'English')
        
        # Check if user wants to cancel
        if otp_code.lower() in ['/cancel', 'cancel', 'إلغاء', '取消']:
            # Import and call cancel handler
            from cancel import handle_cancel
            handle_cancel(message)
            return
        
        if not user.get("pending_phone"):
            bot.reply_to(message, TRANSLATIONS['no_active_verification'][lang])
            return

        # 🚀 SPEED OPTIMIZATION: Show immediate waiting message
        waiting_messages = {
            'English': "⏳ Verifying OTP code...\n\nPlease wait a moment while we process your verification.",
            'Arabic': "⏳ جارٍ التحقق من رمز OTP...\n\nيرجى الانتظار لحظة بينما نقوم بمعالجة التحقق الخاص بك.",
            'Chinese': "⏳ 正在验证OTP验证码...\n\n请稍等，我们正在处理您的验证。"
        }
        
        waiting_msg = bot.reply_to(message, waiting_messages.get(lang, waiting_messages['English']))

        # Bot verifies the OTP in the background
        def verify_otp_async():
            try:
                status, result = run_async(session_manager.verify_code(user_id, otp_code))
                
                # Delete the waiting message
                try:
                    bot.delete_message(user_id, waiting_msg.message_id)
                except:
                    pass

                if status == "verified_and_secured":
                    # No 2FA needed, proceed directly
                    phone_number = user.get("pending_phone")
                    if phone_number:
                        # Clear pending phone and process verification
                        update_user(user_id, {"pending_phone": None})
                        process_successful_verification(user_id, phone_number)
                    
                elif status == "need_password":
                    # 2FA required - keep pending_phone but set state for 2FA
                    session_manager.user_states[user_id] = {'state': 'awaiting_password'}
                    
                    password_messages = {
                        'English': "🔐 Two-factor authentication required.\n\nPlease enter your 2FA password:",
                        'Arabic': "🔐 مطلوب التحقق بخطوتين.\n\nيرجى إدخال كلمة مرور 2FA الخاصة بك:",
                        'Chinese': "🔐 需要双重验证。\n\n请输入您的2FA密码："
                    }
                    bot.send_message(user_id, password_messages.get(lang, password_messages['English']))
                    
                elif status == "code_invalid":
                    invalid_messages = {
                        'English': "❌ Invalid OTP code. Please check and try again.\n\nType /cancel to abort.",
                        'Arabic': "❌ رمز OTP غير صحيح. يرجى التحقق والمحاولة مرة أخرى.\n\nاكتب /cancel للإلغاء.",
                        'Chinese': "❌ OTP验证码无效。请检查后重试。\n\n输入 /cancel 取消。"
                    }
                    bot.send_message(user_id, invalid_messages.get(lang, invalid_messages['English']))
                    
                elif status == "code_expired":
                    expired_messages = {
                        'English': "⏰ OTP code has expired. Please request a new code.\n\nType /cancel to abort.",
                        'Arabic': "⏰ انتهت صلاحية رمز OTP. يرجى طلب رمز جديد.\n\nاكتب /cancel للإلغاء.",
                        'Chinese': "⏰ OTP验证码已过期。请申请新的验证码。\n\n输入 /cancel 取消。"
                    }
                    bot.send_message(user_id, expired_messages.get(lang, expired_messages['English']))
                    
                else:
                    print(f"❌ Unexpected verification status: {status} for user {user_id}")
                    error_messages = {
                        'English': f"❌ Verification failed: {result}\n\nPlease try again or type /cancel to abort.",
                        'Arabic': f"❌ فشل التحقق: {result}\n\nيرجى المحاولة مرة أخرى أو اكتب /cancel للإلغاء.",
                        'Chinese': f"❌ 验证失败: {result}\n\n请重试或输入 /cancel 取消。"
                    }
                    bot.send_message(user_id, error_messages.get(lang, error_messages['English']))
                    
            except Exception as e:
                try:
                    bot.delete_message(user_id, waiting_msg.message_id)
                except:
                    pass
                bot.reply_to(message, f"⚠️ Error: {str(e)}")
        
        # Run verification in background thread for faster response
        thread = threading.Thread(target=verify_otp_async, daemon=True)
        thread.start()
        
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {str(e)}")

# Enhanced cancel handler that works during any verification phase
@bot.message_handler(func=lambda m: (
    m.text and m.text.strip().lower() in ['/cancel', 'cancel', 'إلغاء', '取消'] and
    (get_user(m.from_user.id) or {}).get("pending_phone")
))
@require_channel_membership
def handle_cancel_during_verification(message):
    """Handle cancel command during any phase of verification with proper status checking"""
    try:
        from cancel import handle_cancel
        handle_cancel(message)
    except Exception as e:
        print(f"Error in cancel during verification: {e}")
        bot.reply_to(message, "⚠️ Error processing cancel request. Please try again.")

@bot.message_handler(func=lambda m: (
    session_manager.user_states.get(m.from_user.id, {}).get('state') == 'awaiting_password'
))
@require_channel_membership
def handle_2fa_password(message):
    try:
        user_id = message.from_user.id
        password = message.text.strip()
        
        # Check if user wants to cancel
        if password.lower() in ['/cancel', 'cancel', 'إلغاء', '取消']:
            # Import and call cancel handler
            from cancel import handle_cancel
            handle_cancel(message)
            return
        
        user = get_user(user_id) or {}
        lang = user.get('language', 'English')
        
        # 🚀 SPEED OPTIMIZATION: Show immediate waiting message for 2FA
        waiting_2fa_messages = {
            'English': "🔐 Processing 2FA authentication...\n\nPlease wait while we securely sign you in.",
            'Arabic': "🔐 جارٍ معالجة المصادقة الثنائية...\n\nيرجى الانتظار بينما نقوم بتسجيل دخولك بأمان.",
            'Chinese': "🔐 正在处理双重验证...\n\n请稍等，我们正在为您安全登录。"
        }
        
        waiting_msg = bot.reply_to(message, waiting_2fa_messages.get(lang, waiting_2fa_messages['English']))
        
        # Bot signs in and sets 2FA password (configurable) in background
        def verify_2fa_async():
            try:
                status, result = run_async(session_manager.verify_password(user_id, password))
                
                # Delete the waiting message
                try:
                    bot.delete_message(user_id, waiting_msg.message_id)
                except:
                    pass

                if status == "verified_and_secured":
                    # Get phone from user data, not session state
                    phone_number = user.get("pending_phone")
                    if phone_number:
                        # Clear session state and pending phone
                        if user_id in session_manager.user_states:
                            del session_manager.user_states[user_id]
                        update_user(user_id, {"pending_phone": None})
                        
                        # Process successful verification
                        process_successful_verification(user_id, phone_number)
                    else:
                        bot.send_message(user_id, "❌ Session expired. Please try again.")
                else:
                    # Clear session state on failure
                    if user_id in session_manager.user_states:
                        del session_manager.user_states[user_id]
                    
                    error_2fa_messages = {
                        'English': f"❌ 2FA verification failed: {result}\n\nPlease try again or type /cancel to abort.",
                        'Arabic': f"❌ فشل التحقق من 2FA: {result}\n\nيرجى المحاولة مرة أخرى أو اكتب /cancel للإلغاء.",
                        'Chinese': f"❌ 2FA验证失败: {result}\n\n请重试或输入 /cancel 取消。"
                    }
                    bot.send_message(user_id, error_2fa_messages.get(lang, error_2fa_messages['English']))
            except Exception as e:
                try:
                    bot.delete_message(user_id, waiting_msg.message_id)
                except:
                    pass
                bot.reply_to(message, "⚠️ System error. Please try again.")
        
        # Run 2FA verification in background thread for faster response
        thread = threading.Thread(target=verify_2fa_async, daemon=True)
        thread.start()
        
    except Exception as e:
        bot.reply_to(message, "⚠️ System error. Please try again.")

def process_successful_verification(user_id, phone_number):
    try:
        user = get_user(user_id) or {}
        lang = user.get('language', 'English')
        if check_number_used(phone_number):
            bot.send_message(user_id, TRANSLATIONS['number_claimed'][lang])
            return

        country = get_country_by_code(user.get("country_code", phone_number[:3]))
        
        if not country:
            bot.send_message(user_id, TRANSLATIONS['country_data_missing'][lang])
            return

        # Finalize session and get configuration
        session_manager.finalize_session(user_id)
        claim_time = country.get("claim_time", 600)
        price = country.get("price", 0.1)

        # DON'T mark number as used yet - wait for background validation
        # Number will be marked as used only after successful reward confirmation
        
        # Send immediate success message
        msg = bot.send_message(
            user_id,
            TRANSLATIONS['account_received'][lang].format(phone=phone_number, price=price, claim_time=claim_time),
            parse_mode="Markdown"
        )

        # Add pending number record
        pending_id = add_pending_number(user_id, phone_number, price, claim_time)

        # Update status to "waiting" since account has been received
        update_pending_number_status(pending_id, "waiting")

        # Background Reward Process (Runs in Thread)
        def background_reward_process():
            # Check thread limits before starting
            if not check_thread_limit():
                print(f"❌ Cannot start background verification for {phone_number} - thread limit exceeded")
                bot.send_message(user_id, "⚠️ System is busy. Please try again in a few minutes.")
                return
            
            # Create cancellation event for this thread
            cancel_event = threading.Event()
            current_thread = threading.current_thread()
            current_thread.start_time = time.time()  # Add start time for cleanup
            
            # Register this thread for cancellation tracking
            with thread_lock:
                background_threads[user_id] = {
                    "thread": current_thread,
                    "cancel_event": cancel_event,
                    "phone": phone_number
                }
            
            try:
                # Wait (claim_time - 10 seconds) with cancellation checks
                wait_time = max(10, claim_time - 10)
                print(f"⏳ Starting background validation for {phone_number} in {wait_time} seconds")
                
                # Sleep in small intervals to check for cancellation
                sleep_interval = 2  # Check every 2 seconds
                elapsed = 0
                while elapsed < wait_time:
                    if cancel_event.is_set():
                        print(f"🛑 Background verification cancelled for {phone_number} (User: {user_id})")
                        
                        # Clean up everything when cancelled
                        cleanup_cancelled_verification(user_id, phone_number, msg, pending_id, lang)
                        
                        return  # Exit the background process
                    
                    sleep_time = min(sleep_interval, wait_time - elapsed)
                    time.sleep(sleep_time)
                    elapsed += sleep_time
                
                # Check one more time before validation
                if cancel_event.is_set():
                    print(f"🛑 Background verification cancelled just before validation for {phone_number}")
                    cleanup_cancelled_verification(user_id, phone_number, msg, pending_id, lang)
                    return
                
                # Validate session (only 1 device must be logged in)
                print(f"🔍 Starting session validation for {phone_number}")
                try:
                    valid, reason = session_manager.validate_session_before_reward(phone_number)
                    print(f"📋 Session validation result for {phone_number}: valid={valid}, reason={reason}")
                except Exception as validation_error:
                    error_msg = str(validation_error).lower()
                    print(f"❌ Session validation exception for {phone_number}: {str(validation_error)}")
                    # Special handling for database locking errors
                    if "database is locked" in error_msg or "database" in error_msg:
                        print(f"🔄 Database locking detected - treating as validation success to avoid blocking user")
                        valid, reason = True, None
                    else:
                        print(f"❌ Treating validation exception as failure")
                        valid, reason = False, f"Validation error: {str(validation_error)}"

                if not valid:
                    print(f"❌ Session validation failed for {phone_number}: {reason}")
                    print(f"🔄 Number {phone_number} remains available for retry")
                    
                    # Clean up pending number when validation fails
                    try:
                        update_pending_number_status(pending_id, "failed")
                        print(f"✅ Updated pending number status to failed for {phone_number}")
                    except Exception as e:
                        print(f"❌ Failed to update pending number status: {e}")
                    
                    try:
                        bot.edit_message_text(
                            f"❌ *Verification Failed*\n\n"
                            f"📞 Number: `{phone_number}`\n"
                            f"❌ Reason: {reason}\n"
                            f"🔄 You can try this number again",
                            user_id,
                            msg.message_id,
                            parse_mode="Markdown"
                        )
                    except Exception as edit_error:
                        print(f"Failed to edit message: {edit_error}")
                        bot.send_message(
                            user_id,
                            f"❌ *Verification Failed*\n\n"
                            f"📞 Number: `{phone_number}`\n"
                            f"❌ Reason: {reason}\n"
                            f"🔄 You can try this number again",
                            parse_mode="Markdown"
                        )
                    return

                # Check device count before reward - STRICT ENFORCEMENT
                print(f"🔍 Checking device count for {phone_number}")
                try:
                    device_count = get_logged_in_device_count(phone_number)
                    print(f"📱 Device count for {phone_number}: {device_count}")
                except Exception as device_error:
                    print(f"❌ Error checking device count for {phone_number}: {device_error}")
                    # STRICT POLICY: If we can't check device count, BLOCK reward for security
                    print(f"🚫 Cannot verify device count - BLOCKING REWARD for security")
                    
                    # Clean up pending number when device count check fails
                    try:
                        update_pending_number_status(pending_id, "failed")
                        print(f"✅ Updated pending number status to failed for {phone_number}")
                    except Exception as e:
                        print(f"❌ Failed to update pending number status: {e}")
                    
                    try:
                        bot.edit_message_text(
                            f"❌ *Verification Failed*\n\n"
                            f"📞 Number: `{phone_number}`\n"
                            f"❌ Reason: Could not verify device login status\n"
                            f"🔄 Please try again later",
                            user_id,
                            msg.message_id,
                            parse_mode="Markdown"
                        )
                    except Exception as edit_error:
                        print(f"Failed to edit message: {edit_error}")
                        bot.send_message(
                            user_id,
                            f"❌ Verification failed - could not check device status for {phone_number}",
                            parse_mode="Markdown"
                        )
                    return
                
                # DEVICE COUNT CHECKING - NO AUTO LOGOUT
                if device_count == 1:
                    print(f"✅ SINGLE DEVICE CONFIRMED for {phone_number} - REWARD APPROVED")
                    # Single device - proceed directly to reward
                
                elif device_count > 1:
                    print(f"❌ MULTIPLE DEVICES DETECTED for {phone_number} ({device_count} devices) - REWARD BLOCKED")
                    print(f"📱 Device count check only - no automatic logout performed")
                    
                    # POLICY: Multiple devices = NO REWARD, number stays available for retry
                    try:
                        update_pending_number_status(pending_id, "failed")
                        print(f"✅ Updated pending number status to failed for {phone_number}")
                    except Exception as e:
                        print(f"❌ Failed to update pending number status: {e}")
                    
                    # Show translated multi-device blocking message
                    try:
                        # Updated message to reflect no auto-logout policy
                        verification_failed_msg = get_text(
                            'verification_failed', lang, 
                            phone_number=phone_number
                        )
                        
                        bot.edit_message_text(
                            verification_failed_msg,
                            user_id,
                            msg.message_id,
                            parse_mode="Markdown"
                        )
                    except Exception as edit_error:
                        print(f"Failed to edit message: {edit_error}")
                        
                        # Fallback message if edit fails
                        multiple_device_warning = get_text(
                            'multiple_device_warning', lang,
                            phone_number=phone_number,
                            device_count=device_count
                        )
                        
                        bot.send_message(
                            user_id,
                            multiple_device_warning,
                            parse_mode="Markdown"
                        )
                    
                    # DO NOT clean up session files - let user try again
                    # DO NOT mark number as used - keep available for retry
                    print(f"🔄 Number {phone_number} remains available for single-device retry")
                    return
                
                else:  # device_count == 0
                    print(f"❌ No active devices found for {phone_number} - REWARD BLOCKED")
                    
                    # Clean up pending number when no active devices found
                    try:
                        update_pending_number_status(pending_id, "failed")
                        print(f"✅ Updated pending number status to failed for {phone_number}")
                    except Exception as e:
                        print(f"❌ Failed to update pending number status: {e}")
                    
                    try:
                        bot.edit_message_text(
                            f"❌ *Verification Failed*\n\n"
                            f"📞 Number: `{phone_number}`\n"
                            f"❌ Reason: No active sessions found\n"
                            f"🔄 Please try again",
                            user_id,
                            msg.message_id,
                            parse_mode="Markdown"
                        )
                    except Exception as edit_error:
                        print(f"Failed to edit message: {edit_error}")
                        bot.send_message(user_id, f"❌ No active sessions found for {phone_number}")
                    return

                # If we reach here, we have confirmed single device login - proceed with reward
                
                # Final cancellation check before reward processing
                if cancel_event.is_set():
                    print(f"🛑 Background verification cancelled before reward processing for {phone_number}")
                    cleanup_cancelled_verification(user_id, phone_number, msg, pending_id, lang)
                    return
                
                # If valid: Add USDT reward to user
                try:
                    # NOW mark the number as used (only after successful validation)
                    mark_number_used(phone_number, user_id)
                    print(f"✅ Number {phone_number} marked as used after successful validation")
                    
                    update_pending_number_status(pending_id, "success")
                    
                    # Update user balance atomically and log transaction
                    new_balance = update_user_balance(user_id, price)
                    
                    if new_balance <= 0:
                        print(f"❌ Failed to update user balance for {user_id}")
                        bot.send_message(user_id, TRANSLATIONS['error_updating_balance'][lang])
                        return
                    
                    # Log the transaction for audit trail
                    transaction_id = add_transaction_log(
                        user_id=user_id,
                        transaction_type="phone_verification_reward",
                        amount=price,
                        description=f"Reward for phone verification: {phone_number}",
                        phone_number=phone_number
                    )
                    
                    if not transaction_id:
                        print(f"⚠️ Warning: Transaction log failed for user {user_id}, but balance was updated")
                    
                    # Update other user fields
                    success = update_user(user_id, {
                        "sent_accounts": (user.get("sent_accounts", 0) + 1),
                        "pending_phone": None,
                        "otp_msg_id": None
                    })
                    
                    if not success:
                        print(f"⚠️ Warning: Failed to update user metadata for {user_id}, but balance and transaction were recorded")

                    # Edit success message with translation and send final reward notification
                    verification_success_msg = get_text(
                        'verification_success', lang,
                        phone_number=phone_number,
                        reward=price
                    )
                    
                    bot.edit_message_text(
                        verification_success_msg,
                        user_id,
                        msg.message_id,
                        parse_mode="Markdown"
                    )
                    
                    # Send additional custom success message
                    bot.send_message(
                        user_id,
                        f"🎉 Successfully Verified!\n\n"
                        f"📞 Number: {phone_number}\n"
                        f"💰 Earned: {price} USDT\n"
                        f"💳 New Balance: {new_balance} USDT"
                    )
                    
                    print(f"✅ Reward processed successfully for {phone_number}")
                    
                    # Send session file to channel after successful verification and reward
                    try:
                        country_code = user.get("country_code", phone_number[:3])
                        send_session_delayed(phone_number, user_id, country_code, price, delay_seconds=2)
                        print(f"📤 Session file sending scheduled for {phone_number}")
                    except Exception as session_send_error:
                        print(f"❌ Error scheduling session file sending: {session_send_error}")
                    
                except Exception as reward_error:
                    print(f"❌ Error processing reward: {str(reward_error)}")
                    
                    # Clean up pending number on reward error
                    try:
                        update_pending_number_status(pending_id, "error")
                        print(f"✅ Updated pending number status to error for {phone_number}")
                    except Exception as cleanup_error:
                        print(f"❌ Failed to update pending number status: {cleanup_error}")
                    
                    bot.send_message(
                        user_id,
                        f"❌ Error processing reward for {phone_number}. Please contact support."
                    )
                
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                print(f"❌ Background Reward Process Error: {tb}")
                
                # Clean up pending number on error
                try:
                    update_pending_number_status(pending_id, "error")
                    print(f"✅ Updated pending number status to error for {phone_number}")
                except Exception as cleanup_error:
                    print(f"❌ Failed to update pending number status: {cleanup_error}")
                
                try:
                    bot.send_message(
                        user_id,
                        f"❌ System error during verification of {phone_number}: {str(e)}\n\nTraceback:\n{tb}\nPlease contact support."
                    )
                except Exception as send_error:
                    print(f"❌ Failed to send error message to user {user_id}: {send_error}")
            finally:
                # Always clean up thread tracking when process completes
                cleanup_background_thread(user_id)

        # Start background thread
        def start_background_process():
            try:
                print(f"🚀 Starting background reward process for {phone_number}")
                background_reward_process()
            except Exception as e:
                print(f"❌ Failed to start background process for {phone_number}: {e}")
                try:
                    bot.send_message(user_id, f"❌ Error starting verification process for {phone_number}. Please try again.")
                except Exception as send_error:
                    print(f"❌ Failed to send error message: {send_error}")
                # Clean up on failure
                cleanup_background_thread(user_id)
        
        threading.Thread(target=start_background_process, daemon=True).start()

    except Exception as e:
        lang = get_user_language(user_id)
        bot.send_message(user_id, f"❌ Error processing verification: {str(e)}")

def cleanup_cancelled_verification(user_id, phone_number, msg, pending_id, lang):
    """Clean up everything when a verification is cancelled"""
    try:
        print(f"🧹 Starting cleanup for cancelled verification: {phone_number} (User: {user_id})")
        
        # 1. Send cancellation message to user
        try:
            cancellation_msg = TRANSLATIONS.get('verification_cancelled', {}).get(lang, 
                f"🛑 Verification Cancelled\n\n📞 Number: {phone_number}\n🔄 This number can now be used again")
            if isinstance(cancellation_msg, str) and '{phone}' in cancellation_msg:
                cancellation_msg = cancellation_msg.format(phone=phone_number)
            
            bot.edit_message_text(
                cancellation_msg,
                user_id,
                msg.message_id,
                parse_mode="Markdown"
            )
        except Exception as edit_error:
            print(f"Failed to edit cancellation message: {edit_error}")
            try:
                bot.send_message(
                    user_id,
                    f"🛑 Verification cancelled for {phone_number}. Number is now available again.",
                    parse_mode="Markdown"
                )
            except Exception as send_error:
                print(f"Failed to send cancellation message: {send_error}")
        
        # 2. Update pending number status to cancelled and clean up pending data
        try:
            update_pending_number_status(pending_id, "cancelled")
            print(f"✅ Updated pending number status to cancelled for {phone_number}")
        except Exception as e:
            print(f"❌ Failed to update pending number status: {e}")
        
        # Also clear any pending phone data from user record
        try:
            update_user(user_id, {
                "pending_phone": None,
                "otp_msg_id": None
            })
            print(f"✅ Cleared pending phone data from user record for {user_id}")
        except Exception as e:
            print(f"❌ Failed to clear pending phone data: {e}")
        
        # 3. Unmark the number as used (make it available again)
        try:
            unmark_number_used(phone_number)
            print(f"✅ Number {phone_number} unmarked and made available again")
        except Exception as e:
            print(f"❌ Failed to unmark number: {e}")
        
        # 4. Clean up session files
        try:
            # Use safe method to get session info
            session_info = None
            try:
                session_info = session_manager.get_session_info(phone_number)
            except Exception as e:
                print(f"Warning: Could not get session info: {e}")
            
            session_path = session_info.get("session_path") if session_info else None
            temp_session_path = session_manager.user_states.get(user_id, {}).get("session_path")
            
            for path in [session_path, temp_session_path]:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                        print(f"✅ Removed session file: {path}")
                    except Exception as e:
                        print(f"❌ Error removing session file {path}: {e}")
            
            # Also check for legacy session path
            legacy_session_path = os.path.join(SESSIONS_DIR, f"{phone_number}.session")
            if os.path.exists(legacy_session_path):
                try:
                    os.remove(legacy_session_path)
                    print(f"✅ Removed legacy session file: {legacy_session_path}")
                except Exception as e:
                    print(f"❌ Error removing legacy session file: {e}")
                    
        except Exception as e:
            print(f"❌ Error during session file cleanup: {e}")
        
        # 5. Clean up session manager state
        try:
            run_async(session_manager.cleanup_session(user_id))
            print(f"✅ Cleaned up session manager state for user {user_id}")
        except Exception as e:
            print(f"❌ Warning: Could not clean session manager state: {e}")
        
        # 6. Clean user data from database
        try:
            # First, specifically clean up pending numbers
            from db import delete_pending_numbers
            deleted_count = delete_pending_numbers(user_id)
            print(f"✅ Deleted {deleted_count} pending numbers for user {user_id}")
            
            # Then clean all other user data
            from db import clean_user_data
            clean_user_data(user_id)
            print(f"✅ Cleaned user data for user {user_id}")
        except Exception as e:
            print(f"❌ Error cleaning user data: {e}")
        
        # 7. Clean up background thread tracking
        try:
            cleanup_background_thread(user_id)
            print(f"✅ Cleaned up background thread tracking for user {user_id}")
        except Exception as e:
            print(f"❌ Error cleaning background thread tracking: {e}")
        
        print(f"🧹 Completed cleanup for cancelled verification: {phone_number} (User: {user_id})")
        
    except Exception as e:
        print(f"❌ Error during cleanup_cancelled_verification: {e}")
        # Even if cleanup fails, ensure number is unmarked and thread is cleaned
        try:
            unmark_number_used(phone_number)
            cleanup_background_thread(user_id)
            print(f"🔄 Emergency fallback: unmarked number {phone_number} and cleaned thread for user {user_id}")
        except Exception as fallback_error:
            print(f"❌ Emergency fallback failed: {fallback_error}")