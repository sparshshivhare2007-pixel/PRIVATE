from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.supabase import db

async def handle_buy_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Fetch countries from database
    countries = db.fetch_all("SELECT id, name, flag FROM countries WHERE is_active = TRUE ORDER BY \"order\"")
    
    if not countries:
        await update.message.reply_text("No countries available.")
        return
    
    keyboard = []
    for c in countries:
        keyboard.append([InlineKeyboardButton(f"{c[2]} {c[1]}", callback_data=f"country_{c[0]}")])
    
    keyboard.append([InlineKeyboardButton("◀️ Back to Menu", callback_data="back_to_menu")])
    
    await update.message.reply_text(
        "🌍 **SELECT COUNTRY**\n\nChoose a country:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
