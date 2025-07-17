import telebot
from config import BOT_TOKEN

bot = telebot.TeleBot(BOT_TOKEN)

# Initialize proxy manager with bot instance for notifications
from proxy_manager import proxy_manager
proxy_manager.set_notification_bot(bot)