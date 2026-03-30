from telegram import Update
from telegram.ext import ContextTypes
from bot.keyboards.profile_menu import profile_keyboard
from database.supabase import db
import logging

logger = logging.getLogger(__name__)

async def handle_my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle My Profile button - Show user dashboard"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    # Fetch user from database
    user = db.fetch_one(
        "SELECT user_id, first_name, balance, total_deposit, terms_accepted, fsub_verified FROM users WHERE user_id = %s",
        (user_id,)
    )
    
    if not user:
        # User not found, create one
        db.execute(
            "INSERT INTO users (user_id, first_name, balance, total_deposit) VALUES (%s, %s, %s, %s)",
            (user_id, user_name, 0, 0)
        )
        balance = 0
        total_deposit = 0
        terms_accepted = True
        fsub_verified = False
    else:
        balance = user[2] if user[2] else 0
        total_deposit = user[3] if user[3] else 0
        terms_accepted = user[4] if user[4] else False
        fsub_verified = user[5] if user[5] else False
    
    # Status emojis
    terms_status = "✅ Accepted" if terms_accepted else "❌ Not Accepted"
    fsub_status = "✅ Verified" if fsub_verified else "❌ Not Verified"
    
    text = f"""**ACCOUNT DASHBOARD**

**ID**
**User ID:** `{user_id}`
**Name:** {user_name}

**WALLET DETAILS**
- Balance: ₹{balance:.2f}
- Total Deposit: ₹{total_deposit:.2f}

**ACCOUNT STATUS**
- Terms: {terms_status}
- FSub: {fsub_status}"""
    
    await update.message.reply_text(
        text,
        reply_markup=profile_keyboard(),
        parse_mode='Markdown'
    )
