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

    response = "🔧 *ADMIN COMMAND CENTER* 🔧\n\n"
    response += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    response += "🛠️ *ADMINISTRATION PANEL* 🛠️\n"
    response += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    response += "*1️⃣ COUNTRY MANAGEMENT* 🌍\n"
    response += "• `/add <code> <qty> <price> <sec> [name] [flag]` - Add/update country\n"
    response += "• `/countries` - List all configured countries\n"
    response += "• `/cun <country_code> <quantity>` - Set country capacity\n"
    response += "• `/setprice <country_code> <price>` - Set country price\n"
    response += "• `/settime <country_code> <seconds>` - Set claim time\n"
    response += "• `/numberd <country_code>` - Remove country\n\n"
    
    response += "*2️⃣ PAYMENT & WITHDRAWALS* 💰\n"
    response += "• `/pay <user_id>` - Approve withdrawal for user\n"
    response += "• `/paycard <card_name>` - Approve all withdrawals for card\n"
    response += "• `/rejectpayment <user_id|card:name> [reason]` - Reject withdrawals\n"
    response += "• `/cardw <card_name>` - Check withdrawal stats for card\n"
    response += "• `/card <card_name>` - Add new leader card\n\n"
    
    response += "*3️⃣ USER MANAGEMENT* 👥\n"
    response += "• `/userdel <user_id>` - Delete user and all data\n"
    response += "• `/notice` - Send notification to all users\n"
    response += "• `/cleanusers` - Check for blocked users\n"
    response += "• `/removeblocked` - Remove blocked users\n\n"
    
    response += "*4️⃣ SESSION MANAGEMENT* 📱\n"
    response += "• `/sessions` - View session overview by country\n"
    response += "• `/sessionstats` - Detailed statistics\n"
    response += "• `/migratesessions` - Migrate legacy sessions\n"
    response += "• `/cleanupsessions` - Remove empty folders\n"
    response += "• `/exportsessions` - Export session info to JSON\n\n"
    
    response += "*5️⃣ SESSION DOWNLOAD & EXPORT* 📥\n"
    response += "• `/get +country_code [YYYYMMDD]` - Download sessions (zip)\n"
    response += "• `/getall [+country_code] [YYYYMMDD]` - Download all sessions\n"
    response += "• `/getinfo +country_code [YYYYMMDD]` - Get detailed info\n\n"
    
    response += "*6️⃣ SESSION CLEANUP* 🧹\n"
    response += "• `/deletesessions +country_code [YYYYMMDD]` - Delete sessions\n"
    response += "• `/cleansessionsall` - Delete all session files\n\n"
    
    response += "*7️⃣ DEVICE MONITORING* 📊\n"
    response += "• `/checkdevices +number` - Check device count\n"
    response += "• `/testdevicereward +number` - Test reward eligibility\n"
    response += "• `/devicestatus` - Show device security status\n"
    response += "• `/testfailmessage <language> +number` - Test failure messages\n\n"
    
    response += "*8️⃣ SYSTEM INFORMATION* ℹ️\n"
    response += "• `/admin` - Show this admin command list\n\n"
    
    response += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    response += "🔐 *Admin Access: SUPER ADMIN | Total: 29 Commands*\n"
    response += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

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