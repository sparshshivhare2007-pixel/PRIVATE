from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.supabase import db
import logging

logger = logging.getLogger(__name__)

async def handle_country_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle country selection callback - Show products for selected country"""
    query = update.callback_query
    await query.answer()
    
    # Get country ID from callback data (format: country_123)
    country_id = query.data.replace("country_", "")
    print(f"🔍 Country selected: {country_id}")
    
    # Store selected country in context for later use
    context.user_data['selected_country'] = country_id
    
    # Fetch country name
    country = db.fetch_one(
        "SELECT name FROM countries WHERE id = %s",
        (country_id,)
    )
    country_name = country[0] if country else "Unknown"
    
    # Fetch products for this country
    products = db.fetch_all(
        "SELECT id, year, price, stock FROM products WHERE country_id = %s AND is_active = TRUE AND stock > 0 ORDER BY year DESC",
        (country_id,)
    )
    
    print(f"🔍 Products found for {country_name}: {len(products) if products else 0}")
    
    if not products:
        await query.edit_message_text(
            f"📦 **{country_name.upper()} - ACCOUNTS**\n\n"
            f"No products available for this country.\n\n"
            f"◀️ Go back to select another country.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Back to Countries", callback_data="back_to_countries")]
            ]),
            parse_mode='Markdown'
        )
        return
    
    # Create inline keyboard with products
    keyboard = []
    for p in products:
        product_id = p[0]
        year = p[1]
        price = p[2]
        stock = p[3]
        
        button_text = f"{year} - ₹{price} [{stock}]"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"product_{product_id}")])
    
    keyboard.append([InlineKeyboardButton("◀️ Back to Countries", callback_data="back_to_countries")])
    keyboard.append([InlineKeyboardButton("🏠 Back to Menu", callback_data="back_to_menu")])
    
    # Show products
    await query.edit_message_text(
        f"📦 **{country_name.upper()} - ACCOUNTS**\n\n"
        f"Rate: 1 USDT = ₹90.0\n"
        f"Select a product below:\n",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
