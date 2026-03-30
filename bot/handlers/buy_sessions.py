from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.supabase import db
import logging
from datetime import datetime

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


async def handle_session_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle session purchase confirmation"""
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    await query.answer()
    
    if data.startswith("session_confirm_"):
        product_id = data.replace("session_confirm_", "")
        print(f"🔍 Session confirm: {product_id}")
        
        # Get product details
        product = db.fetch_one(
            "SELECT id, name, year, price, stock, country_name FROM products WHERE id = %s AND category = 'session'",
            (product_id,)
        )
        
        if not product:
            await query.edit_message_text("❌ Product not found!")
            return
        
        product_id_db = product[0]
        product_name = product[1]
        year = product[2]
        price = product[3]
        stock = product[4]
        country_name = product[5]
        
        # Check user balance
        user = db.fetch_one("SELECT balance FROM users WHERE user_id = %s", (user_id,))
        balance = user[0] if user else 0
        
        if balance < price:
            await query.edit_message_text(
                f"❌ **Insufficient Balance!**\n\n"
                f"Your Balance: ₹{balance:.2f}\n"
                f"Required: ₹{price:.2f}\n\n"
                f"Please add funds and try again.",
                parse_mode='Markdown'
            )
            return
        
        # Check stock
        if stock <= 0:
            await query.edit_message_text("❌ Out of stock! Please try again later.")
            return
        
        # Get session from stock
        session_item = db.fetch_one(
            "SELECT id, session_string FROM stock WHERE product_id = %s AND is_sold = FALSE LIMIT 1",
            (product_id_db,)
        )
        
        if not session_item:
            await query.edit_message_text("❌ No session available. Please contact support.")
            return
        
        session_id = session_item[0]
        session_string = session_item[1]
        
        # Update balance
        new_balance = balance - price
        db.execute(
            "UPDATE users SET balance = %s, total_spent = total_spent + %s WHERE user_id = %s",
            (new_balance, price, user_id)
        )
        
        # Mark session as sold
        db.execute(
            "UPDATE stock SET is_sold = TRUE, sold_to = %s, sold_at = NOW() WHERE id = %s",
            (user_id, session_id)
        )
        
        # Update product stock
        new_stock = stock - 1
        db.execute(
            "UPDATE products SET stock = %s WHERE id = %s",
            (new_stock, product_id_db)
        )
        
        # Create order
        order_id = f"SESS_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        db.execute(
            "INSERT INTO orders (order_id, user_id, product_id, product_name, country, amount, category, status, account_details, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (order_id, user_id, product_id_db, product_name, country_name, price, 'session', 'completed', session_string, datetime.now())
        )
        
        await query.edit_message_text(
            f"✅ **PURCHASE SUCCESSFUL!**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 **Product:** {product_name}\n"
            f"🌍 **Country:** {country_name}\n"
            f"📅 **Year:** {year}\n"
            f"💰 **Amount:** ₹{price:.2f}\n"
            f"💳 **Balance Remaining:** ₹{new_balance:.2f}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"**📱 SESSION DETAILS:**\n"
            f"`{session_string}`\n\n"
            f"📌 Go to 'My Profile' → 'My Orders' to view order history.",
            parse_mode='Markdown'
        )
        
        # Send log to admin group
        from config.settings import ADMIN_GROUP_ID
        await context.bot.send_message(
            ADMIN_GROUP_ID,
            f"✅ **New Session Purchase!**\n\n"
            f"👤 User: `{user_id}`\n"
            f"📦 Product: {product_name}\n"
            f"🌍 Country: {country_name}\n"
            f"💰 Amount: ₹{price:.2f}\n"
            f"🆔 Order ID: `{order_id}`",
            parse_mode='Markdown'
        )
