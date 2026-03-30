from telegram import Update
from telegram.ext import ContextTypes
from bot.keyboards.profile_menu import profile_keyboard
from database.supabase import db
import logging

logger = logging.getLogger(__name__)

async def handle_profile_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle profile button callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "deposit_now":
        await query.edit_message_text(
            "💰 **Add Funds**\n\n"
            "Coming soon...\n\n"
            "◀️ Back to Profile",
            reply_markup=profile_keyboard(),
            parse_mode='Markdown'
        )
    
    elif data == "my_orders":
        # Fetch orders from database
        user_id = query.from_user.id
        orders = db.fetch_all(
            "SELECT order_id, product_name, amount, status, created_at FROM orders WHERE user_id = %s ORDER BY created_at DESC LIMIT 10",
            (user_id,)
        )
        
        if not orders:
            await query.edit_message_text(
                "📦 **My Orders**\n\n"
                "You haven't made any purchases yet!\n\n"
                "◀️ Back to Profile",
                reply_markup=profile_keyboard(),
                parse_mode='Markdown'
            )
            return
        
        text = "📦 **My Orders**\n\n"
        for order in orders:
            text += f"🆔 `{order[0]}`\n"
            text += f"📦 {order[1]}\n"
            text += f"💰 ₹{order[2]}\n"
            text += f"📅 {order[4].strftime('%d-%m-%Y')}\n"
            text += f"📊 {order[3].upper()}\n"
            text += "━━━━━━━━━━━━━━━━━━\n"
        
        text += "\n◀️ Back to Profile"
        
        await query.edit_message_text(
            text,
            reply_markup=profile_keyboard(),
            parse_mode='Markdown'
        )
    
    elif data == "my_payments":
        # Fetch payments from database
        user_id = query.from_user.id
        payments = db.fetch_all(
            "SELECT txn_id, amount, method, status, created_at FROM transactions WHERE user_id = %s ORDER BY created_at DESC LIMIT 10",
            (user_id,)
        )
        
        if not payments:
            await query.edit_message_text(
                "📋 **My Payments**\n\n"
                "No payment history found!\n\n"
                "◀️ Back to Profile",
                reply_markup=profile_keyboard(),
                parse_mode='Markdown'
            )
            return
        
        text = "📋 **My Payments**\n\n"
        for payment in payments:
            text += f"🆔 `{payment[0]}`\n"
            text += f"💰 ₹{payment[1]}\n"
            text += f"💳 {payment[2]}\n"
            text += f"📅 {payment[4].strftime('%d-%m-%Y')}\n"
            text += f"📊 {payment[3].upper()}\n"
            text += "━━━━━━━━━━━━━━━━━━\n"
        
        text += "\n◀️ Back to Profile"
        
        await query.edit_message_text(
            text,
            reply_markup=profile_keyboard(),
            parse_mode='Markdown'
        )
