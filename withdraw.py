from bot_init import bot
from db import (
    get_user,
    log_withdrawal,
    check_leader_card,
    get_pending_withdrawal,
    update_user
)
from utils import require_channel_membership
from config import WITHDRAWAL_LOG_CHAT_ID
from translations import get_text
import telebot
import time

# In-memory state to track users waiting for withdrawal input
user_withdraw_state = {}

def check_withdraw_conditions(user_id, balance, withdrawal_type, user_language='English'):
    """Check withdrawal conditions based on withdrawal type"""
    # Check minimum amounts based on withdrawal type
    if withdrawal_type == 'leader_card' and balance < 2.0:
        return get_text('minimum_withdrawal_leader', user_language)
    elif withdrawal_type == 'binance' and balance < 5.0:
        return get_text('minimum_withdrawal_binance', user_language)
    elif withdrawal_type is None and balance < 2.0:  # General check
        return get_text('minimum_withdrawal_general', user_language)
    
    if get_pending_withdrawal(user_id):
        return get_text('pending_withdrawal_exists', user_language)
    return None

def clear_withdraw_state(user_id):
    """Clear withdrawal state for user"""
    if user_id in user_withdraw_state:
        user_withdraw_state.pop(user_id)

@bot.message_handler(commands=['withdraw'])
@require_channel_membership
def handle_withdraw(message):
    # Test message to confirm handler is called
    bot.send_message(message.chat.id, "🔍 TEST: Withdraw command received!")
    
    user_id = message.from_user.id
    user = get_user(user_id) or {}
    balance = user.get('balance', 0.0)
    user_language = user.get('language', 'English')
    
    print(f"🔍 DEBUG: Withdraw command called by user {user_id}, balance: {balance}")
    
    # Clear any existing state first
    clear_withdraw_state(user_id)
    
    # Only check for pending withdrawals, not minimum balance
    if get_pending_withdrawal(user_id):
        error_msg = get_text('pending_withdrawal_exists', user_language)
        bot.send_message(message.chat.id, f"❌ {error_msg}")
        return
    
    print(f"🔍 DEBUG: No pending withdrawal, showing buttons...")
    
    # Show withdrawal options with buttons - ALWAYS show buttons regardless of balance
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup()
    
    # Leader Card option (minimum $2)
    if balance >= 2.0:
        keyboard.add(InlineKeyboardButton(
            f"💳 Leader Card (Min: $2) - Available", 
            callback_data="withdraw_leader_card"
        ))
    else:
        keyboard.add(InlineKeyboardButton(
            f"💳 Leader Card (Min: $2) - Need ${2.0 - balance:.2f} more", 
            callback_data="withdraw_insufficient_leader"
        ))
    
    # Binance Pay ID option (minimum $5)
    if balance >= 5.0:
        keyboard.add(InlineKeyboardButton(
            f"💰 Binance Pay ID (Min: $5) - Available", 
            callback_data="withdraw_binance"
        ))
    else:
        keyboard.add(InlineKeyboardButton(
            f"💰 Binance Pay ID (Min: $5) - Need ${5.0 - balance:.2f} more", 
            callback_data="withdraw_insufficient_binance"
        ))
    
    # Cancel button
    keyboard.add(InlineKeyboardButton("❌ Cancel", callback_data="withdraw_cancel"))
    
    print(f"🔍 DEBUG: Created keyboard with {len(keyboard.keyboard)} rows")
    
    # Send withdrawal options message
    withdrawal_msg = get_text('withdrawal_options', user_language, balance=balance)
    print(f"🔍 DEBUG: Withdrawal message: {withdrawal_msg}")
    
    try:
        bot.send_message(message.chat.id, withdrawal_msg, reply_markup=keyboard, parse_mode="Markdown")
        print(f"🔍 DEBUG: Message sent successfully!")
    except Exception as e:
        print(f"🔍 DEBUG: Error sending message: {e}")
        # Try without markdown
        bot.send_message(message.chat.id, withdrawal_msg, reply_markup=keyboard)

# Callback handler for withdrawal option selection
@bot.callback_query_handler(func=lambda call: call.data.startswith('withdraw_'))
def handle_withdrawal_callback(call):
    """Handle withdrawal option selection"""
    try:
        user_id = call.from_user.id
        user = get_user(user_id) or {}
        balance = user.get('balance', 0.0)
        user_language = user.get('language', 'English')
        
        action = call.data.replace('withdraw_', '')
        
        if action == 'cancel':
            # User cancelled withdrawal
            bot.edit_message_text(
                get_text('withdrawal_cancelled', user_language),
                call.message.chat.id,
                call.message.message_id
            )
            bot.answer_callback_query(call.id, "❌ Withdrawal cancelled")
            clear_withdraw_state(user_id)
            return
        
        elif action == 'insufficient_leader' or action == 'insufficient_binance':
            # User clicked on insufficient balance option
            bot.answer_callback_query(call.id, "❌ Insufficient balance for this option")
            return
        
        elif action == 'leader_card':
            # User selected Leader Card withdrawal
            error_msg = check_withdraw_conditions(user_id, balance, 'leader_card', user_language)
            if error_msg:
                bot.answer_callback_query(call.id, f"❌ {error_msg}")
                return
            
            # Set state for leader card input
            user_withdraw_state[user_id] = {
                "awaiting_input": True,
                "withdrawal_type": "leader_card",
                "balance": balance
            }
            
            # Update message to ask for leader card
            bot.edit_message_text(
                get_text('leader_card_prompt', user_language),
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id, "💳 Enter your leader card name")
        
        elif action == 'binance':
            # User selected Binance Pay ID withdrawal
            error_msg = check_withdraw_conditions(user_id, balance, 'binance', user_language)
            if error_msg:
                bot.answer_callback_query(call.id, f"❌ {error_msg}")
                return
            
            # Set state for Binance Pay ID input
            user_withdraw_state[user_id] = {
                "awaiting_input": True,
                "withdrawal_type": "binance",
                "balance": balance
            }
            
            # Update message to ask for Binance Pay ID
            bot.edit_message_text(
                get_text('binance_id_prompt', user_language),
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id, "💰 Enter your Binance Pay ID")
    
    except Exception as e:
        bot.answer_callback_query(call.id, "⚠️ Error occurred")
        print(f"❌ Withdrawal callback error: {e}")

# Handler for non-command text messages during withdrawal
@bot.message_handler(func=lambda m: (
    hasattr(m, 'text') and 
    m.text and 
    not m.text.startswith('/') and 
    m.from_user.id in user_withdraw_state and
    user_withdraw_state[m.from_user.id].get("awaiting_input", False)
))
@require_channel_membership
def handle_withdrawal_input(message):
    user_id = message.from_user.id
    user_input = message.text.strip()
    user = get_user(user_id) or {}
    user_language = user.get('language', 'English')
    
    if user_id not in user_withdraw_state:
        return
    
    state = user_withdraw_state[user_id]
    withdrawal_type = state.get("withdrawal_type")
    balance = state.get("balance")
    
    if withdrawal_type == "leader_card":
        handle_leader_card_input(message, user_input, balance, user_language)
    elif withdrawal_type == "binance":
        handle_binance_input(message, user_input, balance, user_language)

def handle_leader_card_input(message, card_name, balance, user_language):
    """Handle leader card input"""
    user_id = message.from_user.id
    
    if not check_leader_card(card_name):
        bot.send_message(message.chat.id, get_text('incorrect_leader_card', user_language))
        return
    
    # Log the withdrawal as pending
    log_withdrawal(user_id, balance, card_name, "pending", "leader_card")
    bot.send_message(
        message.chat.id, 
        get_text('withdrawal_submitted_leader', user_language, balance=balance, card_name=card_name)
    )
    
    # Notify admin channel
    bot.send_message(
        WITHDRAWAL_LOG_CHAT_ID,
        get_text('new_withdrawal_request_leader', 'English', user_id=user_id, balance=balance, card_name=card_name)
    )
    
    # Clear user state
    clear_withdraw_state(user_id)

def handle_binance_input(message, binance_id, balance, user_language):
    """Handle Binance Pay ID input"""
    user_id = message.from_user.id
    
    # Basic validation for Binance Pay ID (you can enhance this)
    if len(binance_id) < 5:
        bot.send_message(message.chat.id, get_text('invalid_binance_id', user_language))
        return
    
    # Log the withdrawal as pending
    log_withdrawal(user_id, balance, binance_id, "pending", "binance")
    bot.send_message(
        message.chat.id, 
        get_text('withdrawal_submitted_binance', user_language, balance=balance, binance_id=binance_id)
    )
    
    # Notify admin channel
    bot.send_message(
        WITHDRAWAL_LOG_CHAT_ID,
        get_text('new_withdrawal_request_binance', 'English', user_id=user_id, balance=balance, binance_id=binance_id)
    )
    
    # Clear user state
    clear_withdraw_state(user_id)
