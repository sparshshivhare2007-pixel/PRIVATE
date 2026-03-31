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
    PhoneNumberBannedError,
    FloodWaitError,
)
import asyncio

logger = logging.getLogger(__name__)

# ================= LOGIN SESSION STORAGE =================
login_sessions = {}

API_ID = 20138139
API_HASH = "ff813495ed17a07723000a9751f4c3ee"

# single telethon client (for other uses)
_telethon_client = None


# ================= TELETHON CLIENTS =================
async def get_telethon_client():
    global _telethon_client

    if _telethon_client is None or not _telethon_client.is_connected():
        _telethon_client = TelegramClient("bot_session", API_ID, API_HASH)
        await _telethon_client.connect()
        logger.info("✅ Telethon connected")

    return _telethon_client


async def create_login_client(phone: str):
    """Create fresh client for login to handle DC migration"""
    client = TelegramClient(f"login_{phone}", API_ID, API_HASH)
    await client.connect()
    logger.info(f"✅ Login client created for {phone}")
    return client


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
        "`+919876543210|price`\n\n"
        f"✅ Tips:\n"
        f"• Use REAL numbers (not VoIP)\n"
        f"• Wait 2min for SMS\n"
        f"• Format: `+91xxxxxxxxxx|40`\n\n"
        "Send number now:",
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
            "❌ Format: `+919876543210|40`",
            parse_mode="Markdown",
        )
        return True

    number, price_text = text.split("|", 1)

    try:
        price = float(price_text.strip())
    except Exception:
        await update.message.reply_text("❌ Invalid price (use numbers only).")
        return True

    # Normalize number
    number = number.strip().replace(" ", "").replace("-", "")

    try:
        client = await create_login_client(number)
        
        # 🔥 RETRY LOGIC + FLOOD HANDLING
        result = None
        for attempt in range(3):
            try:
                result = await client.send_code_request(number)
                logger.info(f"✅ OTP sent (attempt {attempt+1}): {number}")
                break
            except FloodWaitError as e:
                wait_time = e.seconds
                logger.warning(f"Flood wait {wait_time}s for {number}")
                await update.message.reply_text(
                    f"⏳ Rate limited. Waiting {wait_time}s...\nTry again in 1min."
                )
                await asyncio.sleep(min(wait_time + 5, 60))
            except PhoneNumberBannedError:
                await update.message.reply_text(
                    f"❌ Number `{number}` is banned by Telegram.",
                    parse_mode="Markdown"
                )
                await client.disconnect()
                return True
            except Exception as retry_e:
                logger.warning(f"OTP attempt {attempt+1} failed: {retry_e}")
                if attempt == 2:
                    raise retry_e
                await asyncio.sleep(3)
        
        if not result:
            raise Exception("No valid result after retries")

        # Store everything
        login_sessions[user_id].update({
            "number": number,
            "price": price,
            "phone_code_hash": result.phone_code_hash,
            "step": "waiting_otp",
            "client": client,
        })

        await update.message.reply_text(
            f"✅ OTP sent to `{number}`\n\n"
            f"📱 Check SMS/Telegram app\n"
            f"⏰ Wait 2min if delayed\n\n"
            f"Send 5-6 digit OTP:",
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.error(f"OTP send FAILED for {number}: {e}")
        error_msg = str(e).lower()
        
        if "phone number" in error_msg and "invalid" in error_msg:
            await update.message.reply_text(f"❌ Invalid number format: `{number}`\nUse `+91xxxxxxxxxx`", parse_mode="Markdown")
        elif "banned" in error_msg:
            await update.message.reply_text(f"❌ `{number}` is banned by Telegram", parse_mode="Markdown")
        elif "flood" in error_msg:
            await update.message.reply_text("❌ Rate limited. Wait 5min and try fresh number.")
        else:
            await update.message.reply_text(f"❌ Failed: `{str(e)[:80]}`\nTry fresh number.")
        
        # Cleanup
        if login_sessions.get(user_id, {}).get("client"):
            try:
                await login_sessions[user_id]["client"].disconnect()
            except:
                pass
        login_sessions.pop(user_id, None)

    return True


# ================= OTP PROCESS =================
async def process_login_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = login_sessions.get(user_id)

    if not session or session.get("step") != "waiting_otp":
        return False

    otp = update.message.text.strip()

    if not otp.isdigit() or len(otp) not in (5, 6):
        await update.message.reply_text("❌ Send 5-6 digit OTP only.")
        return True

    client = session.get("client")
    if not client:
        await update.message.reply_text("❌ Session expired. /login again.")
        login_sessions.pop(user_id, None)
        return True

    try:
        await client.sign_in(
            phone=session["number"],
            code=otp,
            phone_code_hash=session["phone_code_hash"],
        )

        # === DB SAVE ===
        country_id = session["country_id"]
        number = session["number"]
        price = session["price"]

        country = db.fetch_one("SELECT name FROM countries WHERE id=%s", (country_id,))
        country_name = country[0] if country else "Unknown"

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

        password = "".join(random.choices(string.ascii_letters + string.digits, k=8))
        two_fa = "".join(random.choices(string.ascii_letters + string.digits, k=6))

        db.execute(
            "INSERT INTO stock (product_id,number,password,otp,two_fa,is_sold,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (product_id, number, password, otp, two_fa, False, datetime.now()),
        )

        await update.message.reply_text(
            f"🎉 *LOGIN SUCCESS*\n\n"
            f"📱 `{number}`\n"
            f"💰 ₹{price}\n\n"
            f"🔑 Password: `{password}`\n"
            f"🔐 2FA: `{two_fa}`",
            parse_mode="Markdown",
        )
        logger.info(f"✅ Login SUCCESS: {number}")

        # Cleanup
        await client.disconnect()
        login_sessions.pop(user_id, None)

    except PhoneCodeInvalidError:
        await update.message.reply_text("❌ Wrong OTP. Try again.")
        
    except PhoneCodeExpiredError:
        await update.message.reply_text("❌ OTP expired. /login again.")
        await client.disconnect()
        login_sessions.pop(user_id, None)
        
    except SessionPasswordNeededError:
        await update.message.reply_text("❌ 2FA enabled on account.")
        await client.disconnect()
        login_sessions.pop(user_id, None)
        
    except Exception as e:
        logger.error(f"OTP failed for {session.get('number')}: {e}")
        await update.message.reply_text(f"❌ Login error: `{str(e)[:80]}`")
        try:
            await client.disconnect()
        except:
            pass
        login_sessions.pop(user_id, None)

    return True


# ================= CANCEL =================
async def cancel_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    session = login_sessions.get(user_id)
    
    if session and session.get("client"):
        try:
            await session["client"].disconnect()
        except:
            pass
    
    login_sessions.pop(user_id, None)
    await query.edit_message_text("❌ Login cancelled.")
