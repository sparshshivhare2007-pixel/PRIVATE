from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.decorators.admin import admin_only
from database.supabase import db
import logging
import random
import string
from datetime import datetime
from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
)

logger = logging.getLogger(__name__)

# ================= LOGIN SESSION STORAGE =================
login_sessions = {}

API_ID = 20138139
API_HASH = "ff813495ed17a07723000a9751f4c3ee"

# single telethon client
_telethon_client = None


# ================= TELETHON CLIENT =================
async def get_telethon_client():
    global _telethon_client

    if _telethon_client is None or not _telethon_client.is_connected():
        _telethon_client = TelegramClient("bot_session", API_ID, API_HASH)
        await _telethon_client.connect()
        logger.info("✅ Telethon connected")

    return _telethon_client


async def close_telethon_client():
    global _telethon_client

    if _telethon_client:
        try:
            await _telethon_client.disconnect()
        except Exception:
            pass

        _telethon_client = None
        logger.info("🔌 Telethon disconnected")


# ================= LOGIN ROUTER =================
async def login_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Routes login messages BEFORE menu handler.
    Must be called in main.py message handler.
    """
    user_id = update.effective_user.id
    session = login_sessions.get(user_id)

    if not session:
        return False

    step = session.get("step")

    if step == "waiting_number":
        return await process_login_number(update, context)

    if step == "waiting_otp":
        return await process_login_otp(update, context)

    return False


# ================= ADMIN LOGIN =================
@admin_only
async def admin_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    countries = db.fetch_all(
        'SELECT id, name, flag FROM countries WHERE is_active = TRUE ORDER BY "order"'
    )

    if not countries:
        await update.message.reply_text("No countries found.")
        return

    keyboard = [
        [
            InlineKeyboardButton(
                f"{c[2] or '🌍'} {c[1]}",
                callback_data=f"login_country_{c[0]}",
            )
        ]
        for c in countries
    ]

    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_login")])

    await update.message.reply_text(
        "🔐 *Admin Login*\n\nSelect country:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


# ================= COUNTRY SELECT =================
async def handle_login_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    country_id = query.data.replace("login_country_", "")
    user_id = query.from_user.id

    login_sessions[user_id] = {
        "country_id": country_id,
        "step": "waiting_number",
    }

    country = db.fetch_one("SELECT name FROM countries WHERE id=%s", (country_id,))
    country_name = country[0] if country else "Unknown"

    await query.edit_message_text(
        f"🔐 *Login - {country_name}*\n\n"
        "`+919876543210|price`\n\nExample:\n`+919876543210|70`\n\n"
        "Send number now.",
        parse_mode="Markdown",
    )


# ================= NUMBER PROCESS =================
async def process_login_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = login_sessions.get(user_id)

    if not session or session.get("step") != "waiting_number":
        return False

    text = update.message.text.strip()

    if "|" not in text:
        await update.message.reply_text(
            "❌ Format: `+919876543210|price`",
            parse_mode="Markdown",
        )
        return True

    number, price_text = text.split("|")

    try:
        price = float(price_text.strip())
    except Exception:
        await update.message.reply_text("❌ Invalid price.")
        return True

    try:
        client = await get_telethon_client()

        # 🔥 IMPORTANT FIX (OTP expiry solution)
        result = await client.send_code_request(number.strip())

        login_sessions[user_id].update(
            {
                "number": number.strip(),
                "price": price,
                "phone_code_hash": result.phone_code_hash,
                "step": "waiting_otp",
            }
        )

        await update.message.reply_text(
            f"✅ OTP sent to `{number}`\n\nSend OTP now.",
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.error(e)
        await update.message.reply_text(f"❌ Failed sending OTP:\n{e}")

    return True


# ================= OTP PROCESS =================
async def process_login_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = login_sessions.get(user_id)

    if not session or session.get("step") != "waiting_otp":
        return False

    otp = update.message.text.strip()

    if not otp.isdigit():
        await update.message.reply_text("❌ Invalid OTP.")
        return True

    try:
        client = await get_telethon_client()

        # 🔥 FIXED SIGN IN
        await client.sign_in(
            phone=session["number"],
            code=otp,
            phone_code_hash=session["phone_code_hash"],
        )

        country_id = session["country_id"]
        number = session["number"]
        price = session["price"]

        country = db.fetch_one(
            "SELECT name FROM countries WHERE id=%s", (country_id,)
        )
        country_name = country[0]

        product = db.fetch_one(
            "SELECT id FROM products WHERE country_id=%s AND price=%s",
            (country_id, price),
        )

        if not product:
            db.execute(
                "INSERT INTO products (name,price,stock,country_id,country_name,category,is_active,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    f"Telegram Account {country_name}",
                    price,
                    0,
                    country_id,
                    country_name,
                    "account",
                    True,
                    datetime.now(),
                ),
            )

            product = db.fetch_one(
                "SELECT id FROM products WHERE country_id=%s AND price=%s",
                (country_id, price),
            )

        product_id = product[0]

        password = "".join(
            random.choices(string.ascii_letters + string.digits, k=8)
        )
        two_fa = "".join(
            random.choices(string.ascii_letters + string.digits, k=6)
        )

        db.execute(
            "INSERT INTO stock (product_id,number,password,otp,two_fa,is_sold,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (product_id, number, password, otp, two_fa, False, datetime.now()),
        )

        await update.message.reply_text(
            f"🎉 LOGIN SUCCESS\n\n"
            f"📱 `{number}`\n"
            f"💰 ₹{price}\n\n"
            f"Password: `{password}`\n"
            f"2FA: `{two_fa}`",
            parse_mode="Markdown",
        )

        login_sessions.pop(user_id, None)

    except PhoneCodeInvalidError:
        await update.message.reply_text("❌ Wrong OTP.")

    except PhoneCodeExpiredError:
        await update.message.reply_text("❌ OTP expired. Use /login again.")
        login_sessions.pop(user_id, None)

    except SessionPasswordNeededError:
        await update.message.reply_text("❌ Account has 2FA enabled.")
        login_sessions.pop(user_id, None)

    except Exception as e:
        logger.error(e)
        await update.message.reply_text(f"❌ Login failed: {e}")
        login_sessions.pop(user_id, None)

    return True


# ================= CANCEL =================
async def cancel_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    login_sessions.pop(query.from_user.id, None)
    await query.edit_message_text("❌ Login cancelled.")
