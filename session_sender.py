import os
import zipfile
from datetime import datetime
from bot_init import bot
from config import SEND_SESSION_CHANNEL_ID, SESSIONS_DIR
from telegram_otp import session_manager
import threading
import time

def send_session_to_channel(phone_number, user_id, country_code, price):
    """
    Send session file to the specified channel when a successful account is created
    """
    try:
        # Ensure sessions directory exists
        if not os.path.exists(SESSIONS_DIR):
            os.makedirs(SESSIONS_DIR, exist_ok=True)
            print(f"📁 Created sessions directory: {SESSIONS_DIR}")
        
        # Get session file path with improved error handling
        try:
            session_path = session_manager._get_session_path(phone_number)
        except Exception as path_error:
            print(f"❌ Error getting session path for {phone_number}: {path_error}")
            return False
        
        # Check if session file exists with detailed logging
        if not os.path.exists(session_path):
            print(f"❌ Session file not found for {phone_number}")
            print(f"   Expected path: {session_path}")
            
            # Check if session exists in any subdirectory
            if os.path.exists(SESSIONS_DIR):
                for root, dirs, files in os.walk(SESSIONS_DIR):
                    for file in files:
                        if file == f"{phone_number}.session":
                            alt_path = os.path.join(root, file)
                            print(f"   Found session at alternative path: {alt_path}")
                            session_path = alt_path
                            break
                else:
                    print(f"   No session file found anywhere for {phone_number}")
                    return False
            else:
                print(f"   Sessions directory does not exist: {SESSIONS_DIR}")
                return False
        
        # Verify file is not empty and readable
        try:
            file_size = os.path.getsize(session_path)
            if file_size == 0:
                print(f"❌ Session file is empty for {phone_number}")
                return False
        except Exception as size_error:
            print(f"❌ Error checking file size for {phone_number}: {size_error}")
            return False
        
        # Calculate file size
        file_size_mb = file_size / (1024 * 1024)
        
        # Create session info
        session_info = {
            'phone': phone_number,
            'user_id': user_id,
            'country': country_code,
            'price': price,
            'created_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
            'file_size': f"{file_size_mb:.2f} MB"
        }
        
        # Prepare caption
        caption = f"""🎉 **NEW SESSION CREATED** 🎉

📱 **Phone**: `{phone_number}`
👤 **User ID**: `{user_id}`
🌍 **Country**: `{country_code}`
💰 **Price**: `${price}`
📅 **Created**: `{session_info['created_at']}`
📊 **File Size**: `{session_info['file_size']}`

✅ **Session file ready for use!**"""

        # Validate channel ID
        if not SEND_SESSION_CHANNEL_ID:
            print(f"❌ SEND_SESSION_CHANNEL_ID is not configured")
            return False

        # Send the session file with improved error handling
        try:
            with open(session_path, 'rb') as session_file:
                result = bot.send_document(
                    SEND_SESSION_CHANNEL_ID,
                    session_file,
                    caption=caption,
                    parse_mode="Markdown",
                    visible_file_name=f"{phone_number}.session"
                )
                print(f"✅ Session file sent to channel for {phone_number} (Message ID: {result.message_id})")
                return True
        except Exception as send_error:
            print(f"❌ Error sending session file to channel for {phone_number}: {send_error}")
            print(f"   Channel ID: {SEND_SESSION_CHANNEL_ID}")
            print(f"   File path: {session_path}")
            return False
        
    except Exception as e:
        print(f"❌ Unexpected error sending session to channel for {phone_number}: {e}")
        import traceback
        traceback.print_exc()
        return False

def send_session_delayed(phone_number, user_id, country_code, price, delay_seconds=5):
    """
    Send session file to channel after a delay to ensure file is ready
    """
    def delayed_send():
        try:
            print(f"🕐 Starting delayed session send for {phone_number} after {delay_seconds}s delay")
            time.sleep(delay_seconds)
            
            # Verify session file exists before attempting to send
            session_path = session_manager._get_session_path(phone_number)
            max_wait_time = 30  # Wait up to 30 seconds for file to appear
            wait_count = 0
            
            while not os.path.exists(session_path) and wait_count < max_wait_time:
                print(f"⏳ Waiting for session file to be created: {session_path} (wait {wait_count + 1}s)")
                time.sleep(1)
                wait_count += 1
            
            if os.path.exists(session_path):
                success = send_session_to_channel(phone_number, user_id, country_code, price)
                if success:
                    print(f"✅ Delayed session send completed for {phone_number}")
                else:
                    print(f"❌ Delayed session send failed for {phone_number}")
            else:
                print(f"❌ Session file still not found after {max_wait_time}s wait: {session_path}")
        except Exception as e:
            print(f"❌ Error in delayed session send for {phone_number}: {e}")
            import traceback
            traceback.print_exc()
    
    # Run in background thread with better error handling
    try:
        thread = threading.Thread(target=delayed_send, daemon=True, name=f"SessionSender-{phone_number}")
        thread.start()
        print(f"🕐 Scheduled session file sending for {phone_number} in {delay_seconds} seconds")
        return True
    except Exception as e:
        print(f"❌ Error starting session send thread for {phone_number}: {e}")
        return False

def send_bulk_sessions_to_channel(country_code=None, max_files=50):
    """
    Send multiple session files to channel (admin function)
    """
    try:
        sent_count = 0
        
        # Ensure sessions directory exists
        if not os.path.exists(SESSIONS_DIR):
            print(f"❌ Sessions directory does not exist: {SESSIONS_DIR}")
            return 0
        
        if country_code:
            # Send sessions from specific country
            country_dir = os.path.join(SESSIONS_DIR, country_code)
            if os.path.exists(country_dir):
                session_files = [f for f in os.listdir(country_dir) if f.endswith('.session')]
                print(f"📤 Found {len(session_files)} session files for country {country_code}")
                
                for session_file in session_files[:max_files]:
                    session_path = os.path.join(country_dir, session_file)
                    phone_number = session_file.replace('.session', '')
                    
                    try:
                        with open(session_path, 'rb') as file:
                            caption = f"📱 **{phone_number}** (Country: {country_code})\n📅 Bulk export"
                            bot.send_document(
                                SEND_SESSION_CHANNEL_ID,
                                file,
                                caption=caption,
                                parse_mode="Markdown",
                                visible_file_name=session_file
                            )
                        sent_count += 1
                        time.sleep(1)  # Avoid rate limits
                        print(f"✅ Sent {session_file} ({sent_count}/{min(len(session_files), max_files)})")
                    except Exception as e:
                        print(f"❌ Error sending {session_file}: {e}")
            else:
                print(f"❌ Country directory not found: {country_dir}")
        else:
            # Send sessions from all countries
            countries = [d for d in os.listdir(SESSIONS_DIR) if os.path.isdir(os.path.join(SESSIONS_DIR, d))]
            print(f"📤 Found {len(countries)} country directories")
            
            for country in countries:
                country_path = os.path.join(SESSIONS_DIR, country)
                if os.path.isdir(country_path) and sent_count < max_files:
                    session_files = [f for f in os.listdir(country_path) if f.endswith('.session')]
                    
                    for session_file in session_files:
                        if sent_count >= max_files:
                            break
                            
                        session_path = os.path.join(country_path, session_file)
                        phone_number = session_file.replace('.session', '')
                        
                        try:
                            with open(session_path, 'rb') as file:
                                caption = f"📱 **{phone_number}** (Country: {country})\n📅 Bulk export"
                                bot.send_document(
                                    SEND_SESSION_CHANNEL_ID,
                                    file,
                                    caption=caption,
                                    parse_mode="Markdown",
                                    visible_file_name=session_file
                                )
                            sent_count += 1
                            time.sleep(1)  # Avoid rate limits
                            print(f"✅ Sent {session_file} from {country} ({sent_count}/{max_files})")
                        except Exception as e:
                            print(f"❌ Error sending {session_file}: {e}")
        
        print(f"📤 Bulk session sending completed: {sent_count} files sent")
        return sent_count
        
    except Exception as e:
        print(f"❌ Error in bulk session sending: {e}")
        import traceback
        traceback.print_exc()
        return 0

def create_session_zip_and_send(country_code=None, date_filter=None):
    """
    Create a ZIP file of session files and send to channel
    """
    try:
        # Ensure sessions directory exists
        if not os.path.exists(SESSIONS_DIR):
            print(f"❌ Sessions directory does not exist: {SESSIONS_DIR}")
            return False
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if country_code:
            zip_filename = f"sessions_{country_code}_{timestamp}.zip"
        else:
            zip_filename = f"sessions_all_{timestamp}.zip"
        
        zip_path = os.path.join(SESSIONS_DIR, zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            session_count = 0
            
            if country_code:
                country_dir = os.path.join(SESSIONS_DIR, country_code)
                if os.path.exists(country_dir):
                    for session_file in os.listdir(country_dir):
                        if session_file.endswith('.session'):
                            session_path = os.path.join(country_dir, session_file)
                            zipf.write(session_path, f"{country_code}/{session_file}")
                            session_count += 1
                else:
                    print(f"❌ Country directory not found: {country_dir}")
                    return False
            else:
                for country in os.listdir(SESSIONS_DIR):
                    country_path = os.path.join(SESSIONS_DIR, country)
                    if os.path.isdir(country_path):
                        for session_file in os.listdir(country_path):
                            if session_file.endswith('.session'):
                                session_path = os.path.join(country_path, session_file)
                                zipf.write(session_path, f"{country}/{session_file}")
                                session_count += 1
        
        if session_count == 0:
            print(f"❌ No session files found to zip")
            os.remove(zip_path)
            return False
        
        # Send ZIP file to channel
        try:
            with open(zip_path, 'rb') as zip_file:
                caption = f"📦 **SESSION ARCHIVE**\n\n"
                if country_code:
                    caption += f"🌍 **Country**: {country_code}\n"
                else:
                    caption += f"🌍 **Country**: All Countries\n"
                caption += f"📱 **Sessions**: {session_count}\n"
                caption += f"📅 **Created**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                
                bot.send_document(
                    SEND_SESSION_CHANNEL_ID,
                    zip_file,
                    caption=caption,
                    parse_mode="Markdown",
                    visible_file_name=zip_filename
                )
            
            print(f"✅ Session ZIP sent to channel: {zip_filename} ({session_count} sessions)")
        except Exception as send_error:
            print(f"❌ Error sending ZIP file: {send_error}")
            return False
        finally:
            # Clean up ZIP file
            if os.path.exists(zip_path):
                os.remove(zip_path)
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating and sending session ZIP: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_session_send_system():
    """
    Test function to verify session sending system is working correctly
    """
    print("🧪 Testing session sending system...")
    
    # Test 1: Check sessions directory
    print(f"1. Sessions directory: {SESSIONS_DIR}")
    if os.path.exists(SESSIONS_DIR):
        print(f"   ✅ Directory exists")
        
        # List subdirectories
        subdirs = [d for d in os.listdir(SESSIONS_DIR) if os.path.isdir(os.path.join(SESSIONS_DIR, d))]
        print(f"   📁 Country directories: {subdirs}")
        
        # Count session files
        total_sessions = 0
        for subdir in subdirs:
            subdir_path = os.path.join(SESSIONS_DIR, subdir)
            session_files = [f for f in os.listdir(subdir_path) if f.endswith('.session')]
            total_sessions += len(session_files)
            print(f"   📱 {subdir}: {len(session_files)} sessions")
        
        print(f"   📊 Total sessions: {total_sessions}")
    else:
        print(f"   ❌ Directory does not exist")
    
    # Test 2: Check bot configuration
    print(f"2. Bot configuration:")
    print(f"   🤖 Bot token configured: {'Yes' if bot._token else 'No'}")
    print(f"   📢 Send channel ID: {SEND_SESSION_CHANNEL_ID}")
    
    # Test 3: Check if bot can access the channel
    try:
        chat_info = bot.get_chat(SEND_SESSION_CHANNEL_ID)
        print(f"   ✅ Can access channel: {chat_info.title}")
    except Exception as e:
        print(f"   ❌ Cannot access channel: {e}")
    
    # Test 4: Check session_manager import
    try:
        test_phone = "+1234567890"
        test_path = session_manager._get_session_path(test_phone)
        print(f"3. Session manager test:")
        print(f"   📱 Test phone: {test_phone}")
        print(f"   📁 Generated path: {test_path}")
        print(f"   ✅ Session manager working")
    except Exception as e:
        print(f"   ❌ Session manager error: {e}")
    
    return True