from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.supabase import db
import logging

logger = logging.getLogger(__name__)

async def handle_buy_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Buy Sessions button - Show country selection"""
    user_id = update.effective_user.id
    
    print(f"🔍 [DEBUG] handle_buy_sessions called by user: {user_id}")
    
    # Fetch countries from database
    try:
        countries = db.fetch_all(
            "SELECT id, name, flag FROM countries WHERE is_active = TRUE ORDER BY \"order\""
        )
        
        if not countries:
            await update.message.reply_text("No countries available. Please check back later.")
            return
        
        # Create inline keyboard
        keyboard = []
        for c in countries:
            flag = c[2] if c[2] else "🌍"
            keyboard.append([InlineKeyboardButton(f"{flag} {c[1]}", callback_data=f"session_country_{c[0]}")])
        
        keyboard.append([InlineKeyboardButton("◀️ Back to Menu", callback_data="back_to_menu")])
        
        await update.message.reply_text(
            "🌍 **SELECT COUNTRY (SESSIONS)**\n\nChoose a country to see available sessions:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error fetching countries: {e}")
        await update.message.reply_text("❌ Error loading countries. Please try again later.")


async def handle_session_country_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle country selection for sessions"""
    query = update.callback_query
    await query.answer()
    
    # Get country ID from callback data (format: session_country_123)
    country_id = query.data.replace("session_country_", "")
    print(f"🔍 Session country selected: {country_id}")
    
    context.user_data['selected_session_country'] = country_id
    
    # Fetch country name
    country = db.fetch_one("SELECT name FROM countries WHERE id = %s", (country_id,))
    country_name = country[0] if country else "Unknown"
    
    # Fetch sessions for this country (category = 'session')
    sessions = db.fetch_all(
        "SELECT id, name, year, price, stock FROM products WHERE country_id = %s AND category = 'session' AND is_active = TRUE AND stock > 0 ORDER BY year DESC",
        (country_id,)
    )
    
    print(f"🔍 Sessions found for {country_name}: {len(sessions) if sessions else 0}")
    
    if not sessions:
        await query.edit_message_text(
            f"📦 **{country_name.upper()} - SESSIONS**\n\n"
            f"No sessions available for this country.\n\n"
            f"◀️ Go back to select another country.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Back to Countries", callback_data="back_to_session_countries")]
            ]),
            parse_mode='Markdown'
        )
        return
    
    # Create inline keyboard with sessions
    keyboard = []
    for s in sessions:
        session_id = s[0]
        name = s[1]
        year = s[2]
        price = s[3]
        stock = s[4]
        
        button_text = f"{name} - {year} - ₹{price} [{stock}]"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"session_product_{session_id}")])
    
    keyboard.append([InlineKeyboardButton("◀️ Back to Countries", callback_data="back_to_session_countries")])
    keyboard.append([InlineKeyboardButton("🏠 Back to Menu", callback_data="back_to_menu")])
    
    await query.edit_message_text(
        f"📦 **{country_name.upper()} - SESSIONS**\n\n"
        f"Rate: 1 USDT = ₹90.0\n"
        f"Select a session below:\n",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_session_product_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle session product selection"""
    query = update.callback_query
    await query.answer()
    
    product_id = query.data.replace("session_product_", "")
    print(f"🔍 Session product selected: {product_id}")
    
    # Fetch product details
    product = db.fetch_one(
        "SELECT id, name, year, price, stock, country_name FROM products WHERE id = %s AND category = 'session'",
        (product_id,)
    )
    
    if not product:
        await query.edit_message_text(
            "❌ Session not found!\n\nPlease go back and try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Back to Countries", callback_data="back_to_session_countries")]
            ])
        )
        return
    
    product_id_db = product[0]
    product_name = product[1]
    year = product[2]
    price = product[3]
    stock = product[4]
    country_name = product[5]
    
    context.user_data['selected_session'] = {
        'id': product_id_db,
        'name': product_name,
        'year': year,
        'price': price,
        'stock': stock,
        'country': country_name
    }
    
    keyboard = [
        [InlineKeyboardButton("✅ Confirm Purchase", callback_data=f"session_confirm_{product_id_db}")],
        [InlineKeyboardButton("◀️ Back to Sessions", callback_data="back_to_session_products")],
        [InlineKeyboardButton("🏠 Back to Menu", callback_data="back_to_menu")]
    ]
    
    await query.edit_message_text(
        f"📋 **ORDER SUMMARY - SESSION**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 **Product:** {product_name}\n"
        f"🌍 **Country:** {country_name}\n"
        f"📅 **Year:** {year}\n"
        f"💰 **Price:** ₹{price}\n"
        f"📊 **Stock Available:** {stock}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Click **Confirm** to complete your purchase.\n\n"
        f"⚠️ Note: Sessions are auto-delivered after payment.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
