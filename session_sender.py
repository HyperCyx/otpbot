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
        # Get session file path
        session_path = session_manager._get_session_path(phone_number)
        
        if not os.path.exists(session_path):
            print(f"❌ Session file not found for {phone_number}")
            return False
        
        # Get file size
        file_size = os.path.getsize(session_path)
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

        # Send the session file
        with open(session_path, 'rb') as session_file:
            bot.send_document(
                SEND_SESSION_CHANNEL_ID,
                session_file,
                caption=caption,
                parse_mode="Markdown",
                visible_file_name=f"{phone_number}.session"
            )
        
        print(f"✅ Session file sent to channel for {phone_number}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending session to channel for {phone_number}: {e}")
        return False

def send_session_delayed(phone_number, user_id, country_code, price, delay_seconds=5):
    """
    Send session file to channel after a delay to ensure file is ready
    """
    def delayed_send():
        time.sleep(delay_seconds)
        send_session_to_channel(phone_number, user_id, country_code, price)
    
    # Run in background thread
    thread = threading.Thread(target=delayed_send, daemon=True)
    thread.start()
    print(f"🕐 Scheduled session file sending for {phone_number} in {delay_seconds} seconds")

def send_bulk_sessions_to_channel(country_code=None, max_files=50):
    """
    Send multiple session files to channel (admin function)
    """
    try:
        sent_count = 0
        
        if country_code:
            # Send sessions from specific country
            country_dir = os.path.join(SESSIONS_DIR, country_code)
            if os.path.exists(country_dir):
                session_files = [f for f in os.listdir(country_dir) if f.endswith('.session')]
                
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
                    except Exception as e:
                        print(f"❌ Error sending {session_file}: {e}")
        else:
            # Send sessions from all countries
            for country in os.listdir(SESSIONS_DIR):
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
                        except Exception as e:
                            print(f"❌ Error sending {session_file}: {e}")
        
        return sent_count
        
    except Exception as e:
        print(f"❌ Error in bulk session sending: {e}")
        return 0

def create_session_zip_and_send(country_code=None, date_filter=None):
    """
    Create a ZIP file of session files and send to channel
    """
    try:
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
                for country in os.listdir(SESSIONS_DIR):
                    country_path = os.path.join(SESSIONS_DIR, country)
                    if os.path.isdir(country_path):
                        for session_file in os.listdir(country_path):
                            if session_file.endswith('.session'):
                                session_path = os.path.join(country_path, session_file)
                                zipf.write(session_path, f"{country}/{session_file}")
                                session_count += 1
        
        # Send ZIP file to channel
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
        
        # Clean up ZIP file
        os.remove(zip_path)
        
        print(f"✅ Session ZIP sent to channel: {zip_filename} ({session_count} sessions)")
        return True
        
    except Exception as e:
        print(f"❌ Error creating and sending session ZIP: {e}")
        return False