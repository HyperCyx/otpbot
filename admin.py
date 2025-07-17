from bot_init import bot
from db import get_user
from config import ADMIN_IDS
from telegram_otp import session_manager
from utils import require_channel_membership
import os

def is_admin(user_id):
    return user_id in ADMIN_IDS

@bot.message_handler(commands=['admin'])
@require_channel_membership
def handle_admin(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return

    response = """🔧 *ADMIN COMMAND CENTER* 🔧

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                           🛠️ ADMINISTRATION PANEL 🛠️                           ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

**1️⃣ COUNTRY MANAGEMENT** 🌍
┌─────────────────────────────────────────────────────────────────────────────────┐
│ `/add <code> <qty> <price> <sec> [name] [flag]` - Add/update country settings  │
│ `/countries` - List all configured countries                                   │
│ `/cun <country_code> <quantity>` - Set country capacity (legacy)               │
│ `/setprice <country_code> <price>` - Set country price (legacy)                │
│ `/settime <country_code> <seconds>` - Set claim time (legacy)                  │
│ `/numberd <country_code>` - Remove country from system                         │
└─────────────────────────────────────────────────────────────────────────────────┘

**2️⃣ PAYMENT & WITHDRAWALS** 💰
┌─────────────────────────────────────────────────────────────────────────────────┐
│ `/pay <user_id>` - Approve withdrawal for specific user                        │
│ `/paycard <card_name>` - Approve all withdrawals for a leader card             │
│ `/rejectpayment <user_id|card:name> [reason]` - Reject withdrawals             │
│ `/cardw <card_name>` - Check withdrawal stats for leader card                  │
│ `/card <card_name>` - Add new leader card                                      │
└─────────────────────────────────────────────────────────────────────────────────┘

**3️⃣ USER MANAGEMENT** 👥
┌─────────────────────────────────────────────────────────────────────────────────┐
│ `/userdel <user_id>` - Delete user and all their data                          │
│ `/notice` - Send notification to all users (reply with text)                   │
│ `/cleanusers` - Check for users who blocked the bot                            │
│ `/removeblocked` - Remove blocked users from database                          │
└─────────────────────────────────────────────────────────────────────────────────┘

**4️⃣ SESSION MANAGEMENT** 📱
┌─────────────────────────────────────────────────────────────────────────────────┐
│ `/sessions` - View session overview by country                                 │
│ `/sessionstats` - Detailed statistics for each country                         │
│ `/migratesessions` - Migrate legacy sessions to country folders                │
│ `/cleanupsessions` - Remove empty country folders                              │
│ `/exportsessions` - Export session information to JSON                         │
└─────────────────────────────────────────────────────────────────────────────────┘

**5️⃣ SESSION DOWNLOAD & EXPORT** 📥
┌─────────────────────────────────────────────────────────────────────────────────┐
│ `/get +country_code [YYYYMMDD]` - Download sessions for country (zip)          │
│ `/getall [+country_code] [YYYYMMDD]` - Download all sessions (zip)             │
│ `/getinfo +country_code [YYYYMMDD]` - Get detailed session info                │
└─────────────────────────────────────────────────────────────────────────────────┘

**6️⃣ SESSION CLEANUP** 🧹
┌─────────────────────────────────────────────────────────────────────────────────┐
│ `/deletesessions +country_code [YYYYMMDD]` - Delete sessions for country       │
│ `/cleansessionsall` - Delete all session files (global cleanup)               │
└─────────────────────────────────────────────────────────────────────────────────┘

**7️⃣ DEVICE MONITORING** 📊
┌─────────────────────────────────────────────────────────────────────────────────┐
│ `/checkdevices +number` - Check device count for phone number                  │
│ `/testdevicereward +number` - Test reward eligibility                          │
│ `/devicestatus` - Show device security status report                           │
│ `/testfailmessage <language> +number` - Test failure messages                  │
└─────────────────────────────────────────────────────────────────────────────────┘

**8️⃣ SYSTEM INFORMATION** ℹ️
┌─────────────────────────────────────────────────────────────────────────────────┐
│ `/admin` - Show this admin command list                                        │
└─────────────────────────────────────────────────────────────────────────────────┘

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 🔐 Admin Access Level: **SUPER ADMIN** | Total Commands: **29**               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛"""

    bot.reply_to(message, response, parse_mode="Markdown")

@bot.message_handler(commands=['sessions'])
def handle_sessions_command(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        sessions_by_country = session_manager.list_country_sessions()
        
        if not sessions_by_country:
            bot.reply_to(message, "📁 No sessions found")
            return
        
        response = "📊 **Session Overview by Country:**\n\n"
        total_sessions = 0
        
        for country_code, sessions in sessions_by_country.items():
            response += f"🌍 **{country_code}**: {len(sessions)} sessions\n"
            total_sessions += len(sessions)
        
        response += f"\n📈 **Total Sessions**: {total_sessions}"
        
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['sessionstats'])
def handle_session_stats(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        sessions_by_country = session_manager.list_country_sessions()
        
        if not sessions_by_country:
            bot.reply_to(message, "📁 No sessions found")
            return
        
        response = "📊 **Session Statistics:**\n\n"
        
        for country_code, sessions in sessions_by_country.items():
            total_size = sum(session.get('size', 0) for session in sessions)
            avg_size = total_size / len(sessions) if sessions else 0
            
            response += f"🌍 **{country_code}**:\n"
            response += f"   📱 Sessions: {len(sessions)}\n"
            response += f"   💾 Total Size: {total_size:,} bytes\n"
            response += f"   📊 Average: {avg_size:.0f} bytes\n\n"
        
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['migratesessions'])
def handle_migrate_sessions(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        # Import the migration function
        from session_manager import migrate_legacy_sessions
        
        bot.reply_to(message, "🔄 Starting session migration...")
        
        # Run migration
        migrate_legacy_sessions()
        
        bot.reply_to(message, "✅ Session migration completed!")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['cleanupsessions'])
def handle_cleanup_sessions(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        # Import the cleanup function
        from session_manager import cleanup_empty_folders
        
        bot.reply_to(message, "🧹 Starting session cleanup...")
        
        # Run cleanup
        cleanup_empty_folders()
        
        bot.reply_to(message, "✅ Session cleanup completed!")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['exportsessions'])
def handle_export_sessions(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        # Import the export function
        from session_manager import export_session_info
        
        bot.reply_to(message, "📄 Exporting session information...")
        
        # Run export
        export_session_info()
        
        bot.reply_to(message, "✅ Session export completed! Check the generated JSON file.")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")