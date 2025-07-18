import os
from dotenv import load_dotenv

load_dotenv()

# Telegram API
API_ID = int(os.getenv('API_ID', 24925181))
API_HASH = os.getenv('API_HASH', '88ec6570f92434a9db2000d1e78364e9')
BOT_TOKEN = os.getenv('BOT_TOKEN', '8033915874:AAEGOEwc66mH3fNhdYg1s4z6N370hiTcxtc')

# OTP Settings
DEFAULT_2FA_PASSWORD = os.getenv('DEFAULT_2FA_PASSWORD', 'AA@@')

# Database
MONGO_URI = os.getenv('MONGO_URI', "mongodb+srv://noob:K3a4ofLngiMG8Hl9@tele.fjm9acq.mongodb.net/?retryWrites=true&w=majority")

# Channels
REQUESTED_CHANNEL = os.getenv('REQUESTED_CHANNEL', "-1002119088215")
WITHDRAWAL_LOG_CHAT_ID = int(os.getenv('WITHDRAWAL_LOG_CHAT_ID', -1002538505443))
SEND_SESSION_CHANNEL_ID = int(os.getenv('SEND_SESSION_CHANNEL_ID', -1002533345170))
ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '1324269327').split(',')]

# Directories
SESSIONS_DIR = os.getenv('SESSIONS_DIR', "sessions")
VERIFIED_DIR = os.getenv('SESSIONS_DIR', "verified")

# Proxy Configuration
PROXYLIST = os.getenv('PROXYLIST', "p.webshare.io:80:ajimjcrn-rotate:bdkf0k1ybhik")  # Format: IP:Port:username:password, IP:Port:username:password

# Device Configuration
DEFAULT_DEVICE_TYPE = os.getenv('DEFAULT_DEVICE_TYPE', 'windows')  # 'android', 'ios', 'windows', 'random'
CUSTOM_DEVICE_NAME = os.getenv('CUSTOM_DEVICE_NAME', 'Windows 10 Desktop')  # Custom device name if desired
CUSTOM_SYSTEM_VERSION = os.getenv('CUSTOM_SYSTEM_VERSION', 'Windows 10')
CUSTOM_APP_VERSION = os.getenv('CUSTOM_APP_VERSION', '4.14.15 (12345) official')

os.makedirs(SESSIONS_DIR, exist_ok=True)
