from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config.settings import UPI_ID, BINANCE_PAY_ID, USDT_ADDRESS, ADMIN_GROUP_ID
from database.supabase import db
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# Store pending payments
pending_payments = {}

async def handle_add_funds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Add Funds button"""
    user_id = update.effective_user.id
    
    # Get user balance
    user = db.fetch_one("SELECT balance FROM users WHERE user_id = %s", (user_id,))
    balance = user[0] if user else 0
    
    text = f"""💰 **ADD FUNDS**

Wallet Balance: ₹{balance:.2f}

Select Payment Method:"""
    
    keyboard = [
        [InlineKeyboardButton("UPI (Auto - Fast)", callback_data="pay_upi")],
        [InlineKeyboardButton("Crypto (Manual)", callback_data="pay_crypto")],
        [InlineKeyboardButton("◀️ Back to Home", callback_data="back_to_menu")]
    ]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle payment method selection"""
    query = update.callback_query
    data = query.data
    
    if data == "pay_upi":
        qr_path = "assets/qr/upi_qr.png"
        
        text = f"""**UPI PAYMENT (Auto-Verify)**

**UPI ID:** `{UPI_ID}`

**STEPS TO PAY:**
1. Scan QR or Copy UPI ID
2. Pay any amount you want
3. Send the **12-Digit UTR** / Ref No. here

Bot is listening for UTR..."""
        
        if os.path.exists(qr_path):
            with open(qr_path, 'rb') as photo:
                await query.message.reply_photo(
                    photo,
                    caption=text,
                    parse_mode='Markdown'
                )
            await query.delete_message()
        else:
            await query.edit_message_text(text, parse_mode='Markdown')
        
        context.user_data['awaiting_utr'] = True
        
    elif data == "pay_crypto":
        text = f"""**CRYPTO DEPOSIT (USDT)**

**Binance Pay ID:** `{BINANCE_PAY_ID}`

**USDT TRC20 Address:**
`{USDT_ADDRESS}`

⚠️ **Min Deposit:** $1
📌 After payment, upload screenshot below.

Send screenshot after payment for verification."""
        
        await query.edit_message_text(text, parse_mode='Markdown')
        context.user_data['awaiting_crypto_proof'] = True
    
    await query.answer()


async def handle_utr_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle UTR message"""
    user_id = update.effective_user.id
    utr = update.message.text.strip()
    
    if not context.user_data.get('awaiting_utr'):
        return False
    
    if len(utr) != 12 or not utr.isdigit():
        await update.message.reply_text("❌ Invalid UTR. Please send 12-digit UTR.")
        return True
    
    pending_payments[user_id] = {'utr': utr, 'amount': None, 'status': 'pending', 'method': 'UPI'}
    
    await update.message.reply_text(
        f"✅ UTR `{utr}` received!\n\nNow enter the **amount** you paid (in ₹):\nExample: `100`",
        parse_mode='Markdown'
    )
    
    context.user_data['awaiting_utr'] = False
    context.user_data['awaiting_amount'] = True
    return True


async def handle_amount_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle amount entered by user"""
    user_id = update.effective_user.id
    amount_text = update.message.text.strip()
    
    if not context.user_data.get('awaiting_amount'):
        return False
    
    try:
        amount = float(amount_text)
        if amount <= 0:
            raise ValueError
    except:
        await update.message.reply_text("❌ Invalid amount. Enter a valid number.")
        return True
    
    pending = pending_payments.get(user_id)
    if not pending:
        await update.message.reply_text("❌ No pending payment found.")
        context.user_data.pop('awaiting_amount', None)
        return True
    
    pending['amount'] = amount
    pending['user_id'] = user_id
    pending['created_at'] = datetime.now()
    
    # Get user info
    user = db.fetch_one("SELECT username, first_name FROM users WHERE user_id = %s", (user_id,))
    username = user[0] if user else 'No username'
    first_name = user[1] if user else 'Unknown'
    
    # Send to admin group
    mention = f"[{first_name}](tg://user?id={user_id})"
    
    message_text = f"""💰 **NEW PAYMENT PENDING**

👤 **User:** {mention}
🆔 **User ID:** `{user_id}`
📱 **UTR:** `{pending['utr']}`
💰 **Amount:** ₹{amount:.2f}
⏰ **Time:** {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}

@admin Please verify this payment."""
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Verify", callback_data=f"verify_{user_id}_{amount}_{pending['utr']}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}_{amount}_{pending['utr']}")
        ]
    ]
    
    await context.bot.send_message(
        ADMIN_GROUP_ID,
        message_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    await update.message.reply_text(
        f"✅ **Payment Details Received!**\n\n"
        f"UTR: `{pending['utr']}`\n"
        f"Amount: ₹{amount:.2f}\n\n"
        f"Your payment is pending verification. Admin will verify shortly.\n\n"
        f"⏱️ You will be notified once confirmed.",
        parse_mode='Markdown'
    )
    
    context.user_data['awaiting_amount'] = False
    return True


async def handle_admin_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin verification from group"""
    query = update.callback_query
    data = query.data
    await query.answer()
    
    parts = data.split('_')
    action = parts[0]
    user_id = int(parts[1])
    amount = float(parts[2])
    utr = '_'.join(parts[3:])
    
    if action == "verify":
        # Add balance
        db.execute(
            "UPDATE users SET balance = balance + %s, total_deposit = total_deposit + %s WHERE user_id = %s",
            (amount, amount, user_id)
        )
        
        # Record transaction
        db.execute(
            "INSERT INTO transactions (user_id, amount, method, status, utr, verified_at) VALUES (%s, %s, %s, %s, %s, %s)",
            (user_id, amount, 'UPI', 'completed', utr, datetime.now())
        )
        
        # Get new balance
        user = db.fetch_one("SELECT balance FROM users WHERE user_id = %s", (user_id,))
        new_balance = user[0] if user else 0
        
        # Notify user
        await context.bot.send_message(
            user_id,
            f"✅ **Payment Verified!**\n\n"
            f"UTR: `{utr}`\n"
            f"Amount: ₹{amount:.2f}\n"
            f"💰 **New Balance:** ₹{new_balance:.2f}\n\n"
            f"Thank you! 🚀",
            parse_mode='Markdown'
        )
        
        await query.edit_message_text(
            f"✅ **VERIFIED**\n\n"
            f"User: `{user_id}`\n"
            f"Amount: ₹{amount:.2f}\n"
            f"UTR: `{utr}`\n\n"
            f"Balance added successfully.",
            parse_mode='Markdown'
        )
        
    elif action == "reject":
        # Reject payment
        db.execute(
            "INSERT INTO transactions (user_id, amount, method, status, utr) VALUES (%s, %s, %s, %s, %s)",
            (user_id, amount, 'UPI', 'rejected', utr)
        )
        
        await context.bot.send_message(
            user_id,
            f"❌ **Payment Rejected!**\n\n"
            f"UTR: `{utr}`\n"
            f"Amount: ₹{amount:.2f}\n\n"
            f"Please contact support for assistance.",
            parse_mode='Markdown'
        )
        
        await query.edit_message_text(
            f"❌ **REJECTED**\n\n"
            f"User: `{user_id}`\n"
            f"Amount: ₹{amount:.2f}\n"
            f"UTR: `{utr}`\n\n"
            f"User has been notified.",
            parse_mode='Markdown'
        )
    
    # Clean up
    if user_id in pending_payments:
        del pending_payments[user_id]


async def handle_crypto_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle crypto payment screenshot (placeholder)"""
    await update.message.reply_text("🔧 Crypto payments coming soon!")
