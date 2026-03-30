from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.supabase import db
from config.settings import BOT_USERNAME
import logging
from datetime import datetime
import random
import string

logger = logging.getLogger(__name__)

async def handle_earn_money(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Earn Money button"""
    user_id = update.effective_user.id
    user = update.effective_user
    
    # Get user's referral code from database
    user_data = db.fetch_one("SELECT referral_code, balance FROM users WHERE user_id = %s", (user_id,))
    
    if not user_data:
        # Create referral code for user
        referral_code = f"ref_{user_id}"
        db.execute(
            "UPDATE users SET referral_code = %s WHERE user_id = %s",
            (referral_code, user_id)
        )
    else:
        referral_code = user_data[0]
    
    # Generate referral link
    referral_link = f"https://t.me/{BOT_USERNAME}?start={referral_code}"
    
    # Get referral statistics
    referrals = db.fetch_all("SELECT referred_id, total_deposit FROM referrals WHERE referrer_id = %s", (user_id,))
    
    total_referrals = len(referrals) if referrals else 0
    total_deposit_from_refs = sum(r[1] for r in referrals) if referrals else 0
    bonus_earned = (total_deposit_from_refs // 1000) * 20
    
    # Calculate next bonus
    next_bonus_needed = 1000 - (total_deposit_from_refs % 1000)
    if total_deposit_from_refs % 1000 == 0 and total_deposit_from_refs > 0:
        next_bonus_needed = 1000
    
    text = f"""💰 **EARN MONEY & REWARDS**
━━━━━━━━━━━━━━━━━━━━━━
Invite friends and earn bonus balance!

**📊 Your Stats**
- Friends Joined: {total_referrals}
- Friends Deposit: ₹{total_deposit_from_refs}
- Bonus Earned: ₹{bonus_earned}
- Next Bonus: ₹{next_bonus_needed} more deposit

💸 **How it works?**
1. Share your link with friends
2. When your friend deposits total ₹1000
3. You instantly get ₹20 Bonus!

🔗 **Your Referral Link:**
`{referral_link}`

🎁 **Have a Coupon?**
Use /redeem CODE to claim rewards."""
    
    keyboard = [
        [InlineKeyboardButton("📤 Share Link", switch_inline_query=referral_link)],
        [InlineKeyboardButton("📋 Copy Link", callback_data="copy_referral_link")],
        [InlineKeyboardButton("◀️ Back to Menu", callback_data="back_to_menu")]
    ]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_redeem_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /redeem command"""
    user_id = update.effective_user.id
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "❌ Please provide a coupon code.\n\n"
            "Usage: `/redeem CODE`\n\n"
            "Example: `/redeem SPARSH2025`",
            parse_mode='Markdown'
        )
        return
    
    code = args[0].upper()
    
    # Check if code exists and is valid
    coupon = db.fetch_one(
        "SELECT id, reward, status, expiry FROM redeem_codes WHERE code = %s",
        (code,)
    )
    
    if not coupon:
        await update.message.reply_text("❌ Invalid coupon code!")
        return
    
    coupon_id = coupon[0]
    reward = coupon[1]
    status = coupon[2]
    expiry = coupon[3]
    
    if status != 'active':
        await update.message.reply_text("❌ This coupon code has already been used or is inactive!")
        return
    
    if expiry and datetime.now() > expiry:
        await update.message.reply_text("❌ This coupon code has expired!")
        return
    
    # Check if user already used this code
    used = db.fetch_one(
        "SELECT id FROM transactions WHERE coupon_code = %s AND user_id = %s",
        (code, user_id)
    )
    
    if used:
        await update.message.reply_text("❌ You have already used this coupon code!")
        return
    
    # Apply reward
    db.execute(
        "UPDATE users SET balance = balance + %s WHERE user_id = %s",
        (reward, user_id)
    )
    
    # Mark coupon as used
    db.execute(
        "UPDATE redeem_codes SET status = 'used', used_by = %s, used_at = NOW() WHERE id = %s",
        (user_id, coupon_id)
    )
    
    # Record transaction
    db.execute(
        "INSERT INTO transactions (user_id, amount, method, status, coupon_code) VALUES (%s, %s, %s, %s, %s)",
        (user_id, reward, 'COUPON', 'completed', code)
    )
    
    # Get new balance
    user = db.fetch_one("SELECT balance FROM users WHERE user_id = %s", (user_id,))
    new_balance = user[0] if user else 0
    
    await update.message.reply_text(
        f"✅ **Coupon Redeemed Successfully!**\n\n"
        f"🎁 Code: `{code}`\n"
        f"💰 Reward: ₹{reward}\n"
        f"💳 **New Balance:** ₹{new_balance:.2f}\n\n"
        f"Thank you for using our service! 🚀",
        parse_mode='Markdown'
    )


async def handle_copy_referral_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle copy referral link callback"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = db.fetch_one("SELECT referral_code FROM users WHERE user_id = %s", (user_id,))
    referral_code = user_data[0] if user_data else f"ref_{user_id}"
    
    referral_link = f"https://t.me/{BOT_USERNAME}?start={referral_code}"
    
    await query.edit_message_text(
        f"🔗 **Your Referral Link:**\n\n"
        f"`{referral_link}`\n\n"
        f"Share this link with your friends to earn bonuses!",
        parse_mode='Markdown'
    )
