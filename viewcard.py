from bot_init import bot
from config import ADMIN_IDS
from db import get_all_leader_cards
from utils import require_channel_membership
from datetime import datetime

@bot.message_handler(commands=['viewcard'])
@require_channel_membership
def handle_viewcard(message):
    """Admin command to view all leader cards with statistics"""
    admin_id = message.from_user.id
    if admin_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    try:
        # Get all leader cards with statistics
        cards = get_all_leader_cards()
        
        if not cards:
            bot.reply_to(message, "📝 *Leader Cards Overview*\n\n❌ No leader cards found.\n\nUse `/card <name>` to add a new leader card.", parse_mode="Markdown")
            return
        
        # Build response message
        response = "💳 *Leader Cards Overview*\n"
        response += f"📊 Total Cards: `{len(cards)}`\n"
        response += f"🕐 Updated: `{datetime.now().strftime('%H:%M:%S')}`\n\n"
        
        # Sort cards by total amount (highest first)
        cards.sort(key=lambda x: x.get('total_amount', 0), reverse=True)
        
        # Calculate totals across all cards
        total_pending_amount = sum(card.get('pending_amount', 0) for card in cards)
        total_completed_amount = sum(card.get('completed_amount', 0) for card in cards)
        total_pending_count = sum(card.get('pending_count', 0) for card in cards)
        total_completed_count = sum(card.get('completed_count', 0) for card in cards)
        
        # Add summary section
        response += "📈 *Global Summary*\n"
        response += f"⏳ Pending: `{total_pending_count}` requests | `${total_pending_amount:.2f}`\n"
        response += f"✅ Completed: `{total_completed_count}` requests | `${total_completed_amount:.2f}`\n"
        response += f"💰 Grand Total: `${total_pending_amount + total_completed_amount:.2f}`\n\n"
        
        response += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Add individual card details
        for i, card in enumerate(cards, 1):
            card_name = card.get('card_name', 'Unknown')
            pending_count = card.get('pending_count', 0)
            pending_amount = card.get('pending_amount', 0)
            completed_count = card.get('completed_count', 0)
            completed_amount = card.get('completed_amount', 0)
            total_amount = card.get('total_amount', 0)
            
            # Status emoji based on pending withdrawals
            if pending_count > 0:
                status_emoji = "🔶"  # Pending activity
                status_text = f"{pending_count} pending"
            else:
                status_emoji = "✅"  # No pending
                status_text = "up to date"
            
            response += f"{status_emoji} *{i}. {card_name}*\n"
            
            if pending_count > 0:
                response += f"   ⏳ Pending: `{pending_count}` requests | `${pending_amount:.2f}`\n"
            
            if completed_count > 0:
                response += f"   ✅ Completed: `{completed_count}` requests | `${completed_amount:.2f}`\n"
            
            if total_amount > 0:
                response += f"   💰 Total Volume: `${total_amount:.2f}`\n"
            else:
                response += f"   📝 Status: No withdrawal activity\n"
            
            response += "\n"
        
        # Add footer with available commands
        response += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        response += "*Available Commands:*\n"
        response += "• `/paycard <name>` - Approve all pending for a card\n"
        response += "• `/cardw <name>` - View detailed card statistics\n"
        response += "• `/card <name>` - Add new leader card\n"
        response += "• `/viewcard` - Refresh this overview"
        
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error retrieving leader cards: {str(e)}")
        print(f"Error in handle_viewcard: {str(e)}")