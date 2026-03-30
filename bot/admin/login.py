from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.decorators.admin import admin_only
from database.supabase import db
import logging
import random
import string
from datetime import datetime
import asyncio
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError

logger = logging.getLogger(__name__)

# Store login sessions
login_sessions = {}

# Telethon client config
API_ID = 20138139
API_HASH = "ff813495ed17a07723000a9751f4c3ee"
SESSION_NAME = "bot_session"

# Global client reference
_telethon_client = None


async def get_telethon_client():
    """Get or create Telethon client"""
    global _telethon_client
    
    if _telethon_client is None or not _telethon_client.is_connected():
        _telethon_client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await _telethon_client.connect()
        logger.info("✅ Telethon client connected")
    
    return _telethon_client


async def close_telethon_client():
    """Close Telethon client properly"""
    global _telethon_client
    if _telethon_client and _telethon_client.is_connected():
        await _telethon_client.disconnect()
        _telethon_client = None
        logger.info("🔌 Telethon client disconnected")


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
    """Process number and price from admin - Initiate Telegram login"""
    user_id = update.effective_user.id
    session = login_sessions.get(user_id)
    
    print(f"🔍 [DEBUG] process_login_number called for user {user_id}")
    
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
    
    # Store number and price
    login_sessions[user_id] = {
        'country_id': session['country_id'],
        'number': number,
        'price': price,
        'step': 'waiting_otp'
    }
    
    # Initiate Telegram login via Telethon
    try:
        client = await get_telethon_client()
        
        # Send login code to the number
        await client.send_code_request(number)
        
        await update.message.reply_text(
            f"✅ **Number received!**\n\n"
            f"📱 **Number:** `{number}`\n"
            f"💰 **Price:** ₹{price:.2f}\n\n"
            f"🔐 **Login code has been sent to your Telegram account!**\n\n"
            f"Please check your Telegram messages (official Telegram app) for the 5-digit login code.\n"
            f"Send the OTP here to complete login.\n\n"
            f"*If you don't see the code, check your Telegram app or email.*",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Telethon error: {e}")
        await update.message.reply_text(
            f"❌ Failed to send login code. Error: {str(e)}\n\n"
            f"Please check the number and try again.",
            parse_mode='Markdown'
        )
        login_sessions.pop(user_id, None)
    
    return True


async def process_login_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process OTP verification via Telethon"""
    user_id = update.effective_user.id
    session = login_sessions.get(user_id)
    
    print(f"🔍 [DEBUG] process_login_otp called for user {user_id}")
    
    if not session or session.get('step') != 'waiting_otp':
        print("🔍 No active login session or wrong step")
        return False
    
    entered_otp = update.message.text.strip()
    print(f"🔍 Received OTP: {entered_otp}")
    
    if entered_otp == '/cancel':
        login_sessions.pop(user_id, None)
        await update.message.reply_text("❌ Login cancelled.")
        return True
    
    # Validate OTP (5 or 6 digits)
    if not entered_otp.isdigit() or len(entered_otp) not in [5, 6]:
        await update.message.reply_text("❌ Invalid OTP! Please send a 5 or 6-digit code.")
        return True
    
    # Verify OTP via Telethon
    try:
        client = await get_telethon_client()
        number = session['number']
        
        # Sign in with the OTP
        await client.sign_in(number, code=entered_otp)
        
        # ========== LOGIN SUCCESSFUL ==========
        
        # Add number to database
        country_id = session['country_id']
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
        
        # ========== SUCCESS MESSAGE ==========
        success_message = f"""
🎉 **LOGIN SUCCESSFUL!** 🎉

━━━━━━━━━━━━━━━━━━━━━━
📱 **Number:** `{number}`
💰 **Price:** ₹{price:.2f}
🌍 **Country:** {country_name}
━━━━━━━━━━━━━━━━━━━━━━

🔑 **Password:** `{password}`
🔐 **2FA Password:** `{two_fa}`

✅ **Account added to stock successfully!**
📊 **Total stock:** {new_stock}

━━━━━━━━━━━━━━━━━━━━━━
📌 Users can now buy this account!
"""
        
        await update.message.reply_text(
            success_message,
            parse_mode='Markdown'
        )
        
        # Clean up session
        login_sessions.pop(user_id, None)
        print(f"✅ Login completed for number: {number}")
        
    except PhoneCodeInvalidError:
        await update.message.reply_text("❌ Invalid OTP! Please try again.")
        return True
    except SessionPasswordNeededError:
        await update.message.reply_text(
            "❌ Two-factor authentication is enabled on this account.\n"
            "Please disable 2FA or use a different number.",
            parse_mode='Markdown'
        )
        login_sessions.pop(user_id, None)
        return True
    except Exception as e:
        logger.error(f"Telethon sign in error: {e}")
        await update.message.reply_text(f"❌ Login failed: {str(e)}")
        login_sessions.pop(user_id, None)
        return True
    
    return True


async def cancel_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel login process"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id in login_sessions:
        login_sessions.pop(user_id)
    
    await query.edit_message_text("❌ Login cancelled.")
