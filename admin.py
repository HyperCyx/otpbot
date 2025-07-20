from bot_init import bot
from db import get_user
from config import ADMIN_IDS
from telegram_otp import session_manager
from utils import require_channel_membership, reset_channel_verification, get_channel_verification_stats
from session_sender import send_bulk_sessions_to_channel, create_session_zip_and_send, send_session_to_channel, test_session_send_system
from session_cleanup import manual_session_cleanup, get_cleanup_status, enable_session_cleanup, disable_session_cleanup, start_session_cleanup
from auto_cancel_scheduler import (
    get_scheduler_status, force_auto_cancel_check, 
    update_auto_cancel_settings, start_auto_cancel_scheduler, 
    stop_auto_cancel_scheduler
)

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
    response += "• `/viewcard` - View all leader cards overview\n"
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
    response += "• `/sendzip [country_code]` - Send sessions as ZIP file\n"
    response += "• `/testsend` - Test session sending system\n\n"
    
    response += "*9️⃣ AUTO-CANCELLATION SYSTEM* 🤖\n"
    response += "• `/autocancelstatus` - Show auto-cancellation status\n"
    response += "• `/forceautocancel` - Force immediate auto-cancellation check\n"
    response += "• `/autocancelsettings [timeout_minutes]` - Update timeout settings\n"
    response += "• `/enableautocancel` - Enable automatic cancellation\n"
    response += "• `/disableautocancel` - Disable automatic cancellation\n\n"
    
    response += "*🔟 PROXY MANAGEMENT* 🌐\n"
    response += "• `/proxystats` - Show proxy statistics\n"
    response += "• `/resetproxies` - Reset failed proxy list\n"
    response += "• `/reloadproxies` - Reload proxy configuration\n"
    response += "• `/checkproxy` - Test proxy health manually\n\n"
    
    response += "*🔟 DEVICE CONFIGURATION* 📱\n"
    response += "• `/deviceinfo` - Show current device configuration\n"
    response += "• `/setdevice [type]` - Set device type (android/ios/windows/random/custom)\n"
    response += "• `/customdevice [name]` - Set custom device name\n\n"
    
    response += "*1️⃣1️⃣ SESSION CLEANUP* 🧹\n"
    response += "• `/enablecleanup` - Enable auto cleanup (4h)\n"
    response += "• `/disablecleanup` - Disable auto cleanup\n"
    response += "• `/cleanupsessions` - Manual session cleanup\n"
    response += "• `/cleanupstatus` - Show cleanup status\n\n"
    
    response += "*1️⃣2️⃣ SYSTEM INFORMATION* ℹ️\n"
    response += "• `/admin` - Show this admin command list\n\n"
    
    response += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    response += "🔐 *Admin Access: SUPER ADMIN | Total: 43 Commands*\n"
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

@bot.message_handler(commands=['testsend'])
def handle_test_session_send(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ Access denied")
        return
    
    try:
        bot.reply_to(message, "🧪 Testing session sending system...")
        test_session_send_system()
        bot.reply_to(message, "✅ Session send test completed. Check console for detailed output.")
    except Exception as e:
        bot.reply_to(message, f"❌ Test failed: {e}")

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
        import asyncio
        
        # Reload proxies
        proxy_manager.load_proxies()
        
        # Send initial response
        initial_response = f"🔄 *Reloading Proxy Configuration...*\n\n"
        initial_response += f"📊 **Loaded Proxies**: {len(proxy_manager.proxies)}\n"
        if len(proxy_manager.proxies) > 0:
            initial_response += "🔍 Testing proxy health... please wait"
        
        bot.reply_to(message, initial_response, parse_mode="Markdown")
        
        # Test proxies if any are loaded
        if len(proxy_manager.proxies) > 0:
            async def test_and_report():
                await proxy_manager.initial_health_check()
                
                # Send final report
                response = f"✅ *Proxy Configuration Completed*\n\n"
                response += proxy_manager.get_proxy_stats()
                
                bot.send_message(message.chat.id, response, parse_mode="Markdown")
            
            # Run the async function
            try:
                asyncio.create_task(test_and_report())
            except RuntimeError:
                asyncio.run(test_and_report())
        else:
            bot.send_message(message.chat.id, "⚠️ No proxies loaded. Check PROXYLIST configuration.", parse_mode="Markdown")
        
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

# Device Configuration Commands

@bot.message_handler(commands=['deviceinfo'])
def handle_device_info(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        from config import DEFAULT_DEVICE_TYPE, CUSTOM_DEVICE_NAME, CUSTOM_SYSTEM_VERSION, CUSTOM_APP_VERSION
        
        response = "📱 *Device Configuration Information*\n\n"
        response += f"🔧 **Current Device Type**: `{DEFAULT_DEVICE_TYPE}`\n"
        
        if DEFAULT_DEVICE_TYPE == 'custom':
            response += f"📋 **Custom Device Name**: `{CUSTOM_DEVICE_NAME}`\n"
            response += f"💻 **System Version**: `{CUSTOM_SYSTEM_VERSION}`\n"
            response += f"📦 **App Version**: `{CUSTOM_APP_VERSION}`\n"
        
        response += "\n💡 **Available Device Types**:\n"
        response += "• `android` - Random Android devices (Samsung, Pixel, Xiaomi, OnePlus)\n"
        response += "• `ios` - Random iOS devices (iPhone models)\n"
        response += "• `windows` - Random Windows devices (Desktop, PC, Surface)\n"
        response += "• `random` - Mix of all device types\n"
        response += "• `custom` - Use your custom device name\n\n"
        response += "🔧 Use `/setdevice [type]` to change device type\n"
        response += "📝 Use `/customdevice [name]` to set custom device name"
        
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['setdevice'])
def handle_set_device(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "❌ Usage: `/setdevice [android/ios/windows/random/custom]`", parse_mode="Markdown")
            return
        
        device_type = args[1].lower()
        valid_types = ['android', 'ios', 'windows', 'random', 'custom']
        
        if device_type not in valid_types:
            bot.reply_to(message, f"❌ Invalid device type. Valid options: {', '.join(valid_types)}", parse_mode="Markdown")
            return
        
        # Update config (in a real implementation, you'd want to save this to a file or database)
        import config
        config.DEFAULT_DEVICE_TYPE = device_type
        
        response = f"✅ *Device Type Updated*\n\n"
        response += f"📱 **New Device Type**: `{device_type}`\n\n"
        
        if device_type == 'custom':
            response += "💡 Don't forget to set your custom device name with `/customdevice [name]`"
        else:
            response += "🔄 New sessions will now use this device type"
        
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['customdevice'])
def handle_custom_device(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        # Get everything after the command as the device name
        text_parts = message.text.split(' ', 1)
        if len(text_parts) < 2:
            bot.reply_to(message, "❌ Usage: `/customdevice Your Device Name`", parse_mode="Markdown")
            return
        
        device_name = text_parts[1].strip()
        if not device_name:
            bot.reply_to(message, "❌ Device name cannot be empty", parse_mode="Markdown")
            return
        
        # Update config
        import config
        config.CUSTOM_DEVICE_NAME = device_name
        config.DEFAULT_DEVICE_TYPE = 'custom'  # Automatically switch to custom mode
        
        response = f"✅ *Custom Device Name Set*\n\n"
        response += f"📱 **Device Name**: `{device_name}`\n"
        response += f"💻 **System Version**: `{config.CUSTOM_SYSTEM_VERSION}`\n"
        response += f"📦 **App Version**: `{config.CUSTOM_APP_VERSION}`\n\n"
        response += "🔄 Device type automatically set to `custom`\n"
        response += "🆕 New sessions will use this device name"
        
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['cleanupsessions'])
@require_channel_membership
def handle_cleanup_sessions_manual(message):
    """Manual session cleanup command"""
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    try:
        bot.reply_to(message, "🧹 Starting manual session cleanup...")
        
        # Perform manual cleanup
        cleaned_count = manual_session_cleanup()
        
        # Get cleanup status
        status = get_cleanup_status()
        
        response = f"✅ **Manual Session Cleanup Completed**\n\n"
        response += f"🗑️ **Cleaned Files**: {cleaned_count}\n"
        response += f"🔄 **Auto Cleanup**: {'Running' if status['running'] else 'Stopped'}\n"
        response += f"⏰ **Cleanup Interval**: {status['cleanup_interval_hours']} hours\n"
        response += f"📅 **Max Session Age**: {status['max_session_age_hours']} hours\n\n"
        response += "💡 Temporary sessions older than 24 hours are automatically removed"
        
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error during session cleanup: {str(e)}")

@bot.message_handler(commands=['cleanupstatus'])
@require_channel_membership  
def handle_cleanup_status(message):
    """Show session cleanup status"""
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    try:
        status = get_cleanup_status()
        
        response = f"🧹 **Session Cleanup Status**\n\n"
        response += f"⚙️ **Auto Cleanup**: {'✅ Enabled' if status['enabled'] else '❌ Disabled'}\n"
        response += f"🔄 **Currently Running**: {'✅ Yes' if status['running'] else '❌ No'}\n"
        response += f"🧵 **Thread Status**: {'✅ Active' if status['thread_alive'] else '❌ Inactive'}\n"
        response += f"⏰ **Cleanup Interval**: {status['cleanup_interval_hours']} hours\n"
        response += f"📅 **Max Session Age**: {status['max_session_age_hours']} hours\n\n"
        response += "💡 **Commands**: `/enablecleanup` | `/disablecleanup` | `/cleanupsessions`"
        
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error getting cleanup status: {str(e)}")

@bot.message_handler(commands=['enablecleanup'])
@require_channel_membership  
def handle_enable_cleanup(message):
    """Enable automatic session cleanup"""
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    try:
        # Enable cleanup
        enabled = enable_session_cleanup()
        
        if enabled:
            # Try to start the scheduler
            started = start_session_cleanup()
            
            if started:
                response = f"✅ **Session Cleanup Enabled**\n\n"
                response += f"🔄 **Status**: Auto cleanup is now running\n"
                response += f"⏰ **Schedule**: Every 4 hours\n"
                response += f"📅 **Target**: Sessions older than 24 hours\n\n"
                response += "💡 The cleanup will run automatically in the background"
            else:
                response = f"⚠️ **Cleanup Enabled but Not Started**\n\n"
                response += f"✅ **Setting**: Auto cleanup enabled\n"
                response += f"❌ **Scheduler**: Failed to start\n\n"
                response += "💡 Try restarting the bot or use `/cleanupstatus` to check"
        else:
            response = "❌ Failed to enable session cleanup"
        
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error enabling cleanup: {str(e)}")

@bot.message_handler(commands=['disablecleanup'])
@require_channel_membership  
def handle_disable_cleanup(message):
    """Disable automatic session cleanup"""
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    try:
        # Disable cleanup (this also stops any running scheduler)
        disabled = disable_session_cleanup()
        
        if disabled:
            response = f"❌ **Session Cleanup Disabled**\n\n"
            response += f"🛑 **Status**: Auto cleanup is now stopped\n"
            response += f"🧹 **Manual**: You can still use `/cleanupsessions`\n"
            response += f"⚙️ **Re-enable**: Use `/enablecleanup` to turn it back on\n\n"
            response += "💡 Session files will not be automatically cleaned"
        else:
            response = "❌ Failed to disable session cleanup"
        
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error disabling cleanup: {str(e)}")

# Channel verification management commands
@bot.message_handler(commands=['channelstats'])
@require_channel_membership
def handle_channel_stats(message):
    """Show channel verification statistics"""
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    try:
        stats = get_channel_verification_stats()
        
        if "error" in stats:
            bot.reply_to(message, f"❌ Error getting stats: {stats['error']}")
            return
        
        response = (
            f"📊 **Channel Verification Statistics**\n\n"
            f"👥 **Total Users**: {stats['total_users']:,}\n"
            f"✅ **Verified Users**: {stats['verified_users']:,}\n"
            f"⏳ **Unverified Users**: {stats['unverified_users']:,}\n"
            f"📈 **Verification Rate**: {stats['verification_rate']:.1f}%\n\n"
            f"ℹ️ *Verified users skip channel checks*"
        )
        
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error getting channel stats: {str(e)}")

@bot.message_handler(commands=['resetchannel'])
@require_channel_membership
def handle_reset_channel(message):
    """Reset channel verification for a user"""
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    try:
        args = message.text.split()
        if len(args) != 2:
            bot.reply_to(message, "Usage: /resetchannel <user_id>\nExample: /resetchannel 123456789")
            return
        
        target_user_id = int(args[1])
        
        # Check if user exists
        user = get_user(target_user_id)
        if not user:
            bot.reply_to(message, f"❌ User {target_user_id} not found in database.")
            return
        
        # Reset verification
        success = reset_channel_verification(target_user_id)
        
        if success:
            response = (
                f"✅ **Channel Verification Reset**\n\n"
                f"👤 **User ID**: {target_user_id}\n"
                f"📝 **Name**: {user.get('name', 'Unknown')}\n"
                f"🔄 **Status**: Verification cache cleared\n\n"
                f"ℹ️ *User will need to verify channel membership again*"
            )
        else:
            response = f"❌ Failed to reset channel verification for user {target_user_id}"
        
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except ValueError:
        bot.reply_to(message, "❌ Invalid user ID. Please provide a valid number.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error resetting channel verification: {str(e)}")

@bot.message_handler(commands=['resetallchannels'])
@require_channel_membership
def handle_reset_all_channels(message):
    """Reset channel verification for all users (nuclear option)"""
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    try:
        # Confirm this is a dangerous operation
        bot.reply_to(message, 
            "⚠️ **WARNING: This will reset ALL channel verifications!**\n\n"
            "All users will need to verify channel membership again.\n"
            "Send `/confirmresetall` to proceed or any other message to cancel.",
            parse_mode="Markdown"
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['confirmresetall'])
@require_channel_membership
def handle_confirm_reset_all(message):
    """Confirm and execute reset of all channel verifications"""
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    try:
        from db import db
        
        # Reset all users' channel verification
        result = db.users.update_many(
            {"channel_verified": True},
            {"$set": {"channel_verified": False}}
        )
        
        response = (
            f"🔄 **ALL Channel Verifications Reset**\n\n"
            f"📊 **Users affected**: {result.modified_count:,}\n"
            f"⚠️ **Status**: All users must verify again\n\n"
            f"ℹ️ *Channel verification cache cleared globally*"
        )
        
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error resetting all channel verifications: {str(e)}")

# Auto-Cancellation System Commands

@bot.message_handler(commands=['autocancelstatus'])
@require_channel_membership
def handle_auto_cancel_status(message):
    """Show auto-cancellation status"""
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    try:
        status = get_scheduler_status()
        
        stats = status.get('stats', {})
        
        response = f"""🤖 **AUTO-CANCELLATION STATUS**

⚙️ **System Status**:
• Enabled: {'✅ Yes' if status.get('enabled', False) else '❌ No'}
• Running: {'✅ Yes' if status.get('running', False) else '❌ No'}
• Timeout: {status.get('timeout_minutes', 30)} minutes
• Check Interval: {status.get('check_interval_minutes', 5)} minutes

📊 **Statistics**:
• Numbers with background verification: {stats.get('numbers_with_background_verification', 0)}
• Numbers without background verification: {stats.get('numbers_without_background_verification', 0)}
• Total auto-cancelled: {stats.get('auto_cancelled_count', 0)}

🔒 **PROTECTION**: Numbers without background verification are NEVER auto-cancelled"""
        
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error getting auto-cancellation status: {str(e)}")

@bot.message_handler(commands=['forceautocancel'])
@require_channel_membership
def handle_force_auto_cancel(message):
    """Force an immediate auto-cancellation check"""
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    try:
        force_auto_cancel_check()
        bot.reply_to(message, "✅ **Force Auto-Cancellation Check Executed**\n\n"
            "The system will now check for and cancel numbers with background verification that are past their timeout.\n\n"
            "🔒 Numbers WITHOUT background verification are protected and will NOT be cancelled.",
            parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Error forcing auto-cancellation check: {str(e)}")

@bot.message_handler(commands=['autocancelsettings'])
@require_channel_membership
def handle_auto_cancel_settings(message):
    """Update auto-cancellation settings"""
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "❌ Usage: `/autocancelsettings [timeout_minutes]`")
            return
        
        timeout_minutes = int(args[1])
        if timeout_minutes <= 0:
            bot.reply_to(message, "❌ Timeout must be a positive integer.")
            return
        
        update_auto_cancel_settings(timeout_minutes=timeout_minutes)
        bot.reply_to(message, f"✅ **Auto-Cancellation Settings Updated**\n\n"
             f"🔄 **New Timeout**: {timeout_minutes} minutes\n"
             f"📅 **Target**: Numbers with background verification older than {timeout_minutes} minutes\n"
             f"🔒 **Protection**: Numbers WITHOUT background verification remain protected\n"
             f"💡 **Commands**: `/enableautocancel` | `/disableautocancel` | `/forceautocancel`",
             parse_mode="Markdown")
    except ValueError:
        bot.reply_to(message, "❌ Invalid timeout value. Please provide a positive integer.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error updating auto-cancellation settings: {str(e)}")

@bot.message_handler(commands=['enableautocancel'])
@require_channel_membership
def handle_enable_auto_cancel(message):
    """Enable automatic cancellation"""
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    try:
        enabled = start_auto_cancel_scheduler()
        
        if enabled:
            status = get_scheduler_status()
            response = f"✅ **Auto-Cancellation Enabled**\n\n"
            response += f"🔄 **Status**: Auto-cancellation is now running\n"
            response += f"⏰ **Schedule**: Every {status.get('check_interval_minutes', 5)} minutes\n"
            response += f"📅 **Target**: Numbers with background verification older than {status.get('timeout_minutes', 30)} minutes\n"
            response += f"🔒 **Protection**: Numbers WITHOUT background verification are NEVER cancelled\n\n"
            response += "💡 The system will automatically cancel only numbers with background verification."
        else:
            response = "❌ Failed to enable auto-cancellation"
        
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error enabling auto-cancellation: {str(e)}")

@bot.message_handler(commands=['disableautocancel'])
@require_channel_membership
def handle_disable_auto_cancel(message):
    """Disable automatic cancellation"""
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    try:
        disabled = stop_auto_cancel_scheduler()
        
        if disabled:
            response = f"❌ **Auto-Cancellation Disabled**\n\n"
            response += f"🛑 **Status**: Auto-cancellation is now stopped\n"
            response += f"🧹 **Manual**: You can still use `/forceautocancel` to check manually\n"
            response += f"⚙️ **Re-enable**: Use `/enableautocancel` to turn it back on\n\n"
            response += "💡 Numbers will not be automatically cancelled (manual cancellation still works)"
        else:
            response = "❌ Failed to disable auto-cancellation"
        
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error disabling auto-cancellation: {str(e)}")