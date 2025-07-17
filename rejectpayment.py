from bot_init import bot
from config import ADMIN_IDS
from db import (
    reject_withdrawals_by_user,
    reject_withdrawals_by_card,
    get_user
)
from utils import require_channel_membership
import re

def notify_user_rejection(user_id, withdrawals, reason="No reason provided"):
    """Send rejection notification to user with custom reason"""
    total_amount = sum(w['amount'] for w in withdrawals)
    try:
        bot.send_message(
            user_id,
            f"❌ *Withdrawal Rejected* ❌\n\n"
            f"💰 **Amount**: ${total_amount}\n"
            f"📋 **Reason**: {reason}\n"
            f"📉 **Balance deducted**: ${total_amount}\n\n"
            f"💬 Contact support if you have questions about this rejection.\n"
            f"🔄 You can make a new withdrawal request if eligible.",
            parse_mode="Markdown"
        )
        print(f"✅ Notified user {user_id} about rejection (${total_amount}) - Reason: {reason}")
    except Exception as e:
        print(f"Could not notify user {user_id}: {str(e)}")

@bot.message_handler(commands=['rejectpayment'])
@require_channel_membership
def handle_reject_payment(message):
    admin_id = message.from_user.id
    if admin_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return

    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, 
            "Usage:\n"
            "/rejectpayment <user_id> [reason]\n"
            "/rejectpayment card:<card_name> [reason]\n"
            "Example: /rejectpayment 12345 Invalid card\n"
            "Example: /rejectpayment card:john_doe Verification failed")
        return

    target = parts[1].strip()
    reason = ' '.join(parts[2:]) if len(parts) > 2 else "No reason provided"

    # Check if rejecting by card
    if target.startswith("card:"):
        card_name = target[5:]  # Remove 'card:' prefix
        count, withdrawals = reject_withdrawals_by_card(card_name, reason)
        if count > 0:
            # Notify each affected user with reason
            user_withdrawals = {}
            for w in withdrawals:
                user_id = w['user_id']
                if user_id not in user_withdrawals:
                    user_withdrawals[user_id] = []
                user_withdrawals[user_id].append(w)
            
            # Send notifications with custom reason
            for user_id, user_w_list in user_withdrawals.items():
                notify_user_rejection(user_id, user_w_list, reason)
            
            total_amount = sum(w['amount'] for w in withdrawals)
            bot.reply_to(message, 
                f"✅ *Payment Rejection Completed*\n\n"
                f"💳 **Card**: {card_name}\n"
                f"📊 **Withdrawals**: {count}\n"
                f"💰 **Total Amount**: ${total_amount}\n"
                f"📋 **Reason**: {reason}\n"
                f"👥 **Users Notified**: {len(user_withdrawals)}\n"
                f"📉 **Balances Deducted**: Yes",
                parse_mode="Markdown")
        else:
            bot.reply_to(message, f"❌ No pending withdrawals found for card: {card_name}")
        return

    # Otherwise treat as user ID
    try:
        user_id = int(target)
        user = get_user(user_id)
        if not user:
            bot.reply_to(message, f"❌ User {user_id} not found")
            return

        count, withdrawals = reject_withdrawals_by_user(user_id, reason)
        if count > 0:
            notify_user_rejection(user_id, withdrawals, reason)
            total_amount = sum(w['amount'] for w in withdrawals)
            bot.reply_to(message, 
                f"✅ *Payment Rejection Completed*\n\n"
                f"👤 **User ID**: {user_id}\n"
                f"📊 **Withdrawals**: {count}\n"
                f"💰 **Total Amount**: ${total_amount}\n"
                f"📋 **Reason**: {reason}\n"
                f"📉 **Balance Deducted**: ${total_amount}\n"
                f"📨 **User Notified**: Yes",
                parse_mode="Markdown")
        else:
            bot.reply_to(message, f"❌ No pending withdrawals found for user {user_id}")
    except ValueError:
        bot.reply_to(message, "❌ User ID must be a number or use card:<name> format")