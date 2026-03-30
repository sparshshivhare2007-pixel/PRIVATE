from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.supabase import db
import logging

logger = logging.getLogger(__name__)

async def handle_buy_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Buy Accounts button - Show country selection"""
    user_id = update.effective_user.id
    
    print(f"🔍 [DEBUG] handle_buy_accounts called by user: {user_id}")
    
    # Fetch countries from database
    try:
        countries = db.fetch_all(
            "SELECT id, name, flag FROM countries WHERE is_active = TRUE ORDER BY \"order\""
        )
        
        print(f"🔍 Countries found: {len(countries) if countries else 0}")
        
        if not countries:
            await update.message.reply_text("No countries available. Please check back later.")
            return
        
        # Create inline keyboard
        keyboard = []
        for c in countries:
            flag = c[2] if c[2] else "🌍"
            keyboard.append([InlineKeyboardButton(f"{flag} {c[1]}", callback_data=f"country_{c[0]}")])
        
        keyboard.append([InlineKeyboardButton("◀️ Back to Menu", callback_data="back_to_menu")])
        
        await update.message.reply_text(
            "🌍 **SELECT COUNTRY**\n\nChoose a country to see available products:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error fetching countries: {e}")
        await update.message.reply_text("❌ Error loading countries. Please try again later.")
