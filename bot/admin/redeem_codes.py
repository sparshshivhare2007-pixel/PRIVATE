from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.decorators.admin import admin_only
from database.supabase import db
import logging
import random
import string
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Store admin states
admin_states = {}


@admin_only
async def create_redeem_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create redeem code - /createcode <reward> <quantity> [days]"""
    args = context.args
    
    if len(args) < 2:
        await update.message.reply_text(
            "❌ **Usage:** /createcode <reward> <quantity> [days]\n\n"
            "📌 **Examples:**\n"
            "`/createcode 50 10` - 10 codes worth ₹50 each (30 days expiry)\n"
            "`/createcode 100 5 7` - 5 codes worth ₹100 each (7 days expiry)\n\n"
            "Users can redeem with: `/redeem CODE`",
            parse_mode='Markdown'
        )
        return
    
    reward = float(args[0])
    quantity = int(args[1])
    expiry_days = int(args[2]) if len(args) > 2 else 30
    
    codes = []
    created_codes = []
    
    for _ in range(quantity):
        # Generate random 8-character code
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        codes.append(code)
        
        # Insert into database
        db.execute(
            "INSERT INTO redeem_codes (code, reward, status, created_by, expiry, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
            (code, reward, 'active', update.effective_user.id, datetime.now() + timedelta(days=expiry_days), datetime.now())
        )
        created_codes.append(code)
    
    # Format codes for display
    codes_text = '\n'.join([f"`{c}`" for c in created_codes])
    
    await update.message.reply_text(
        f"✅ **Redeem Codes Created!**\n\n"
        f"💰 **Reward:** ₹{reward}\n"
        f"🔢 **Quantity:** {quantity}\n"
        f"📅 **Expiry:** {expiry_days} days\n\n"
        f"**Codes:**\n{codes_text}\n\n"
        f"Users can redeem with: `/redeem CODE`",
        parse_mode='Markdown'
    )


@admin_only
async def list_active_codes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all active redeem codes - /codes"""
    codes = db.fetch_all(
        "SELECT code, reward, expiry, created_at FROM redeem_codes WHERE status = 'active' ORDER BY created_at DESC LIMIT 20"
    )
    
    if not codes:
        await update.message.reply_text("No active codes found.")
        return
    
    text = "🎁 **Active Redeem Codes**\n\n"
    for c in codes:
        code = c[0]
        reward = c[1]
        expiry = c[2]
        created = c[3]
        
        expiry_str = expiry.strftime('%d-%m-%Y') if expiry else 'No expiry'
        text += f"🔹 `{code}`\n"
        text += f"   💰 ₹{reward} | 📅 Expires: {expiry_str}\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')


@admin_only
async def list_used_codes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List used redeem codes - /usedcodes"""
    codes = db.fetch_all(
        "SELECT code, reward, used_by, used_at FROM redeem_codes WHERE status = 'used' ORDER BY used_at DESC LIMIT 20"
    )
    
    if not codes:
        await update.message.reply_text("No used codes found.")
        return
    
    text = "📋 **Used Redeem Codes**\n\n"
    for c in codes:
        code = c[0]
        reward = c[1]
        used_by = c[2]
        used_at = c[3]
        
        used_at_str = used_at.strftime('%d-%m-%Y %H:%M') if used_at else 'Unknown'
        text += f"🔹 `{code}`\n"
        text += f"   💰 ₹{reward} | 👤 User: `{used_by}`\n"
        text += f"   📅 Used: {used_at_str}\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')


@admin_only
async def disable_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Disable a redeem code - /disablecode <code>"""
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "❌ **Usage:** /disablecode <code>\n\n"
            "📌 **Example:** `/disablecode ABC12345`\n\n"
            "Use `/codes` to see active codes.",
            parse_mode='Markdown'
        )
        return
    
    code = args[0].upper()
    
    # Check if code exists
    existing = db.fetch_one(
        "SELECT code, status FROM redeem_codes WHERE code = %s",
        (code,)
    )
    
    if not existing:
        await update.message.reply_text(f"❌ Code `{code}` not found!", parse_mode='Markdown')
        return
    
    if existing[1] != 'active':
        await update.message.reply_text(f"⚠️ Code `{code}` is already {existing[1]}!", parse_mode='Markdown')
        return
    
    # Disable the code
    db.execute(
        "UPDATE redeem_codes SET status = 'disabled' WHERE code = %s",
        (code,)
    )
    
    await update.message.reply_text(
        f"✅ Code `{code}` has been disabled!\n\n"
        f"This code can no longer be redeemed.",
        parse_mode='Markdown'
    )


@admin_only
async def enable_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enable a disabled redeem code - /enablecode <code>"""
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "❌ **Usage:** /enablecode <code>\n\n"
            "📌 **Example:** `/enablecode ABC12345`",
            parse_mode='Markdown'
        )
        return
    
    code = args[0].upper()
    
    # Check if code exists
    existing = db.fetch_one(
        "SELECT code, status FROM redeem_codes WHERE code = %s",
        (code,)
    )
    
    if not existing:
        await update.message.reply_text(f"❌ Code `{code}` not found!", parse_mode='Markdown')
        return
    
    if existing[1] == 'active':
        await update.message.reply_text(f"⚠️ Code `{code}` is already active!", parse_mode='Markdown')
        return
    
    if existing[1] == 'used':
        await update.message.reply_text(f"❌ Code `{code}` has already been used and cannot be enabled!", parse_mode='Markdown')
        return
    
    # Enable the code
    db.execute(
        "UPDATE redeem_codes SET status = 'active' WHERE code = %s",
        (code,)
    )
    
    await update.message.reply_text(
        f"✅ Code `{code}` has been enabled!\n\n"
        f"Users can now redeem this code.",
        parse_mode='Markdown'
    )


@admin_only
async def code_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show redeem code statistics - /codestats"""
    # Get counts
    active = db.fetch_one("SELECT COUNT(*) FROM redeem_codes WHERE status = 'active'")
    used = db.fetch_one("SELECT COUNT(*) FROM redeem_codes WHERE status = 'used'")
    disabled = db.fetch_one("SELECT COUNT(*) FROM redeem_codes WHERE status = 'disabled'")
    total = db.fetch_one("SELECT COUNT(*) FROM redeem_codes")
    
    # Get total reward given
    total_reward = db.fetch_one("SELECT COALESCE(SUM(reward), 0) FROM redeem_codes WHERE status = 'used'")
    
    active_count = active[0] if active else 0
    used_count = used[0] if used else 0
    disabled_count = disabled[0] if disabled else 0
    total_count = total[0] if total else 0
    total_reward_amount = total_reward[0] if total_reward else 0
    
    text = f"📊 **Redeem Code Statistics**\n\n"
    text += f"🎁 **Total Codes:** {total_count}\n"
    text += f"✅ **Active:** {active_count}\n"
    text += f"📋 **Used:** {used_count}\n"
    text += f"🚫 **Disabled:** {disabled_count}\n\n"
    text += f"💰 **Total Rewards Given:** ₹{total_reward_amount:.2f}"
    
    await update.message.reply_text(text, parse_mode='Markdown')


@admin_only
async def create_bulk_codes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create bulk redeem codes - /bulkcodes"""
    admin_states[update.effective_user.id] = {'action': 'waiting_bulk_codes'}
    
    await update.message.reply_text(
        "🎁 **Create Bulk Redeem Codes**\n\n"
        "Send me the details in this format:\n\n"
        "`reward: 50`\n"
        "`quantity: 10`\n"
        "`expiry: 30` (days, optional)\n\n"
        "Example:\n"
        "`reward: 100`\n"
        "`quantity: 5`\n"
        "`expiry: 7`\n\n"
        "Type /cancel to cancel.",
        parse_mode='Markdown'
    )


@admin_only
async def process_bulk_codes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process bulk code creation"""
    user_id = update.effective_user.id
    state = admin_states.get(user_id)
    
    if not state or state.get('action') != 'waiting_bulk_codes':
        return False
    
    text = update.message.text.strip()
    
    if text == '/cancel':
        admin_states.pop(user_id, None)
        await update.message.reply_text("❌ Operation cancelled.")
        return True
    
    # Parse details
    reward = None
    quantity = None
    expiry_days = 30
    
    for line in text.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip().lower()
            value = value.strip()
            
            if key == 'reward':
                reward = float(value)
            elif key == 'quantity':
                quantity = int(value)
            elif key == 'expiry':
                expiry_days = int(value)
    
    if not reward or not quantity:
        await update.message.reply_text(
            "❌ Invalid format! Please send:\n\n"
            "`reward: 50`\n"
            "`quantity: 10`\n\n"
            "Type /cancel to cancel.",
            parse_mode='Markdown'
        )
        return True
    
    # Create codes
    codes = []
    for _ in range(quantity):
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        codes.append(code)
        
        db.execute(
            "INSERT INTO redeem_codes (code, reward, status, created_by, expiry, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
            (code, reward, 'active', user_id, datetime.now() + timedelta(days=expiry_days), datetime.now())
        )
    
    # Format codes
    codes_text = '\n'.join([f"`{c}`" for c in codes])
    
    await update.message.reply_text(
        f"✅ **{quantity} Redeem Codes Created!**\n\n"
        f"💰 **Reward:** ₹{reward}\n"
        f"📅 **Expiry:** {expiry_days} days\n\n"
        f"**Codes:**\n{codes_text}\n\n"
        f"Users can redeem with: `/redeem CODE`",
        parse_mode='Markdown'
    )
    
    admin_states.pop(user_id, None)
    return True
