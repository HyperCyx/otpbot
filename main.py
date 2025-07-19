import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from bot_init import bot
import start
import account
import cap
import withdraw
import withdrawhistory
import cun
import setprice
import settime
import numberd
import cancel
import otp
import userdel
import pay
import card
import paycard
import cardw
import viewcard
import rejectpayment
import admin
import notice
import help
import add_country
import admin_sessions
import admin_delete_sessions
import device_sessions
import admin_device_check
import session_cleanup
import temp_session_cleanup
import threading
from flask import Flask, jsonify

# Create Flask app for health checks
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"message": "Telegram Bot is running", "status": "active"})

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def main():
    print("Bot is running...")
    
    # Start Flask server in a separate thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Start the temporary session cleanup scheduler (always enabled)
    temp_session_cleanup.start_cleanup_scheduler()
    
    # Session cleanup is disabled by default - admin must enable it
    print("🧹 Session cleanup is DISABLED by default - use /enablecleanup to turn it on")
    
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"Bot crashed: {str(e)}")
        # Stop session cleanup on shutdown if running
        session_cleanup.stop_session_cleanup()
        temp_session_cleanup.stop_cleanup_scheduler()
        # Add any cleanup or restart logic here

if __name__ == "__main__":
    main()