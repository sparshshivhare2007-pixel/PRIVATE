from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.decorators.admin import admin_only
from database.supabase import db
import logging
import random
import string
from datetime import datetime

logger = logging.getLogger(__name__)

# Store login sessions
login_sessions = {}


@admin_only
async def admin_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin login - Show countries to select number for"""
    user_id = update.effective_user.id
    
    # Fetch countries
    countries = db.fetch_all("SELECT id, name, flag FROM countries WHERE is_active = TRUE ORDER BY \"order\"")
    
    if not countries:
        await update.message.reply_text("No countries found. Add a country first.")
        return
    
    keyboard = []
    for c in countries:
        flag = c[2] if c[2] else "🌍"
        keyboard.append([InlineKeyboardButton(f"{flag} {c[1]}", callback_data=f"login_country_{c[0]}")])
    
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_login")])
    
    await update.message.reply_text(
        "🔐 **Admin Login**\n\nSelect country to add number:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_login_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle country selection for login"""
    query = update.callback_query
    await query.answer()
    
    country_id = query.data.replace("login_country_", "")
    user_id = query.from_user.id
    
    login_sessions[user_id] = {
        'country_id': country_id,
        'step': 'waiting_number'
    }
    
    # Get country name
    country = db.fetch_one("SELECT name FROM countries WHERE id = %s", (country_id,))
    country_name = country[0] if country else "Unknown"
    
    await query.edit_message_text(
        f"🔐 **Login - {country_name}**\n\n"
        f"Send the number in this format:\n"
        f"`+919876543210|price`\n\n"
        f"Example: `+919876543210|70`\n\n"
        f"Price is in ₹.\n\n"
        f"Type /cancel to cancel.",
        parse_mode='Markdown'
    )


async def process_login_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process number and price from admin"""
    user_id = update.effective_user.id
    session = login_sessions.get(user_id)
    
    # Debug print
    print(f"🔍 [DEBUG] process_login_number called for user {user_id}")
    print(f"🔍 Session: {session}")
    
    if not session or session.get('step') != 'waiting_number':
        print("🔍 No active login session or wrong step")
        return False
    
    text = update.message.text.strip()
    print(f"🔍 Received text: {text}")
    
    if text == '/cancel':
        login_sessions.pop(user_id, None)
        await update.message.reply_text("❌ Login cancelled.")
        return True
    
    if '|' not in text:
        await update.message.reply_text(
            "❌ Invalid format! Use: `+919876543210|price`\n\n"
            "Example: `+919876543210|70`",
            parse_mode='Markdown'
        )
        return True
    
    parts = text.split('|')
    number = parts[0].strip()
    try:
        price = float(parts[1].strip())
    except:
        await update.message.reply_text("❌ Invalid price! Enter a valid number.")
        return True
    
    # Generate OTP
    otp = ''.join(random.choices(string.digits, k=6))
    
    # Store session
    login_sessions[user_id] = {
        'country_id': session['country_id'],
        'number': number,
        'price': price,
        'otp': otp,
        'step': 'waiting_otp'
    }
    
    await update.message.reply_text(
        f"✅ Number received!\n\n"
        f"📱 **Number:** `{number}`\n"
        f"💰 **Price:** ₹{price:.2f}\n\n"
        f"🔑 **OTP:** `{otp}`\n\n"
        f"Please verify OTP to complete login.\n"
        f"Send the OTP to confirm.",
        parse_mode='Markdown'
    )
    return True


async def process_login_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process OTP verification"""
    user_id = update.effective_user.id
    session = login_sessions.get(user_id)
    
    # Debug print
    print(f"🔍 [DEBUG] process_login_otp called for user {user_id}")
    print(f"🔍 Session: {session}")
    
    if not session or session.get('step') != 'waiting_otp':
        print("🔍 No active login session or wrong step")
        return False
    
    entered_otp = update.message.text.strip()
    print(f"🔍 Received OTP: {entered_otp}")
    
    if entered_otp == '/cancel':
        login_sessions.pop(user_id, None)
        await update.message.reply_text("❌ Login cancelled.")
        return True
    
    if entered_otp != session['otp']:
        await update.message.reply_text("❌ Invalid OTP! Try again.")
        return True
    
    # OTP verified - Add number to database
    country_id = session['country_id']
    number = session['number']
    price = session['price']
    
    # Get country name
    country = db.fetch_one("SELECT name FROM countries WHERE id = %s", (country_id,))
    country_name = country[0] if country else "Unknown"
    
    # Get or create product for this country
    product = db.fetch_one(
        "SELECT id FROM products WHERE country_id = %s AND name = 'Telegram Account' AND price = %s",
        (country_id, price)
    )
    
    if not product:
        # Create new product
        db.execute(
            "INSERT INTO products (name, price, year, stock, country_id, country_name, category, is_active, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (f"Telegram Account {country_name}", price, 2025, 0, country_id, country_name, 'account', True, datetime.now())
        )
        product = db.fetch_one(
            "SELECT id FROM products WHERE country_id = %s AND name = 'Telegram Account' AND price = %s",
            (country_id, price)
        )
    
    if not product:
        await update.message.reply_text("❌ Failed to create product!")
        login_sessions.pop(user_id, None)
        return True
    
    product_id = product[0]
    
    # Generate random password and 2FA
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    two_fa = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    
    # Add to stock
    db.execute(
        "INSERT INTO stock (product_id, number, password, otp, two_fa, is_sold, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (product_id, number, password, entered_otp, two_fa, False, datetime.now())
    )
    
    # Update product stock count
    stock_count = db.fetch_one("SELECT COUNT(*) FROM stock WHERE product_id = %s AND is_sold = FALSE", (product_id,))
    new_stock = stock_count[0] if stock_count else 0
    db.execute("UPDATE products SET stock = %s WHERE id = %s", (new_stock, product_id))
    
    await update.message.reply_text(
        f"✅ **Login Successful!**\n\n"
        f"📱 **Number:** `{number}`\n"
        f"💰 **Price:** ₹{price:.2f}\n"
        f"🔑 **Password:** `{password}`\n"
        f"🔐 **2FA Password:** `{two_fa}`\n\n"
        f"Account added to stock successfully!\n"
        f"📊 **Total stock:** {new_stock}",
        parse_mode='Markdown'
    )
    
    # Clean up session
    login_sessions.pop(user_id, None)
    return True


async def cancel_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel login process"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id in login_sessions:
        login_sessions.pop(user_id)
    
    await query.edit_message_text("❌ Login cancelled.")
