from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.supabase import db
import logging

logger = logging.getLogger(__name__)

async def handle_product_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle product selection callback - Show order summary"""
    query = update.callback_query
    await query.answer()
    
    # Get product ID from callback data (format: product_123)
    product_id = query.data.replace("product_", "")
    print(f"🔍 Product selected: {product_id}")
    
    # Fetch product details from database
    product = db.fetch_one(
        "SELECT id, name, year, price, stock, country_name FROM products WHERE id = %s AND is_active = TRUE",
        (product_id,)
    )
    
    if not product:
        await query.edit_message_text(
            "❌ Product not found!\n\nPlease go back and try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Back to Countries", callback_data="back_to_countries")]
            ])
        )
        return
    
    product_id_db = product[0]
    product_name = product[1]
    year = product[2]
    price = product[3]
    stock = product[4]
    country_name = product[5]
    
    print(f"🔍 Product: {product_name} | Year: {year} | Price: ₹{price} | Stock: {stock}")
    
    # Store product info in context for purchase
    context.user_data['selected_product'] = {
        'id': product_id_db,
        'name': product_name,
        'year': year,
        'price': price,
        'stock': stock,
        'country': country_name
    }
    
    # Create order summary
    keyboard = [
        [InlineKeyboardButton("✅ Confirm Purchase", callback_data=f"purchase_confirm_{product_id_db}")],
        [InlineKeyboardButton("◀️ Back to Products", callback_data="back_to_products")],
        [InlineKeyboardButton("🏠 Back to Menu", callback_data="back_to_menu")]
    ]
    
    await query.edit_message_text(
        f"📋 **ORDER SUMMARY**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 **Product:** {product_name}\n"
        f"🌍 **Country:** {country_name}\n"
        f"📅 **Year:** {year}\n"
        f"💰 **Price:** ₹{price}\n"
        f"📊 **Stock Available:** {stock}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Click **Confirm** to complete your purchase.\n\n"
        f"⚠️ Note: Accounts are auto-delivered after payment.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
