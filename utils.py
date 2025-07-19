from datetime import datetime
from db import get_user, update_user
from bot_init import bot
from config import REQUESTED_CHANNEL
import telebot.types

# Translation dictionary for all user-facing messages
TRANSLATIONS = {
    'channel_verification': {
        'English': "⚠️ *Channel Verification Required*\n\nTo use this bot, you must join our channel first.\n\nAfter joining, send /start again.",
        'Arabic': "⚠️ *مطلوب التحقق من القناة*\n\nلاستخدام هذا البوت، يجب عليك الانضمام إلى قناتنا أولاً.\n\nبعد الانضمام، أرسل /start مرة أخرى.",
        'Chinese': "⚠️ *需要频道验证*\n\n要使用此机器人，您必须先加入我们的频道。\n\n加入后，请再次发送 /start。"
    }
}

def get_user_language(user_id):
    user = get_user(user_id)
    if user and user.get('language'):
        return user['language']
    return 'English'

def require_channel_membership(func):
    def wrapped(message, *args, **kwargs):
        user_id = message.from_user.id
        
        # Get or create user
        user = get_user(user_id)
        if not user:
            update_user(user_id, {
                'name': message.from_user.first_name,
                'username': message.from_user.username,
                'balance': 0.0,
                'sent_accounts': 0,
                'registered_at': datetime.utcnow(),
                'channel_verified': False  # Initialize channel verification status
            })
            user = get_user(user_id)
        
        # Check if user has permanent channel verification
        if user.get('channel_verified', False):
            print(f"✅ User {user_id} has permanent channel verification - skipping check")
            return func(message, *args, **kwargs)
        
        print(f"🔍 Checking channel membership for user {user_id} (not cached)")
        
        try:
            chat_member = bot.get_chat_member(REQUESTED_CHANNEL, user_id)
            if chat_member.status not in ['member', 'administrator', 'creator']:
                # User is not a member - show verification message
                _send_channel_verification_message(message, user_id)
                return
            else:
                # User is a member - cache this verification permanently
                print(f"✅ User {user_id} verified as channel member - caching permanently")
                update_user(user_id, {'channel_verified': True})
                
        except Exception as e:
            print(f"❌ Error checking channel membership for user {user_id}: {e}")
            # On error, still require verification (don't cache)
            _send_channel_verification_message(message, user_id)
            return
        
        return func(message, *args, **kwargs)
    return wrapped

def _send_channel_verification_message(message, user_id):
    """Helper function to send channel verification message"""
    lang = get_user_language(user_id)
    text = TRANSLATIONS['channel_verification'][lang]
    
    # Create inline keyboard with "Join Now" button
    markup = telebot.types.InlineKeyboardMarkup()
    join_button = telebot.types.InlineKeyboardButton(
        text="Join Now", 
        url="https://t.me/+AWczWKG8V6s3OGY1"
    )
    markup.add(join_button)
    
    bot.send_message(
        message.chat.id,
        text,
        parse_mode="Markdown",
        reply_markup=markup
    )

def reset_channel_verification(user_id: int) -> bool:
    """Reset channel verification status for a user (admin function)"""
    try:
        result = update_user(user_id, {'channel_verified': False})
        if result:
            print(f"🔄 Reset channel verification for user {user_id}")
        return result
    except Exception as e:
        print(f"❌ Error resetting channel verification for user {user_id}: {e}")
        return False

def get_channel_verification_stats() -> dict:
    """Get statistics about channel verification cache"""
    try:
        from db import db
        
        total_users = db.users.count_documents({})
        verified_users = db.users.count_documents({"channel_verified": True})
        unverified_users = total_users - verified_users
        
        return {
            "total_users": total_users,
            "verified_users": verified_users,
            "unverified_users": unverified_users,
            "verification_rate": (verified_users / total_users * 100) if total_users > 0 else 0
        }
    except Exception as e:
        print(f"❌ Error getting channel verification stats: {e}")
        return {"error": str(e)}
