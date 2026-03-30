from telegram import Update
from telegram.ext import ContextTypes
from bot.handlers.buy_accounts import handle_buy_accounts
from bot.handlers.profile import handle_my_profile
from bot.handlers.add_funds import handle_add_funds
from bot.keyboards.main_menu import main_menu
import logging

logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages from main menu"""
    text = update.message.text
    user_id = update.effective_user.id
    
    # Skip if it's a command
    if text.startswith('/'):
        return
    
    print(f"🔍 [DEBUG] Menu button clicked: '{text}'")
    
    # Main menu options
    if text == "🛒 Buy Accounts":
        print("🔍 Calling handle_buy_accounts...")
        await handle_buy_accounts(update, context)
    
    elif text == "🛍️ Buy Sessions":
        print("🔍 Calling buy sessions...")
        await update.message.reply_text("🛍️ Buy Sessions\n\nComing soon...")
    
    elif text == "💰 Add Funds":
        print("🔍 Calling add funds...")
        await handle_add_funds(update, context)
    
    elif text == "💵 Earn Money":
        print("🔍 Calling earn money...")
        await update.message.reply_text("💵 Earn Money\n\nComing soon...")
    
    elif text == "👤 My Profile":
        print("🔍 Calling my profile...")
        await handle_my_profile(update, context)
    
    elif text == "❓ How to Use":
        print("🔍 Calling how to use...")
        await update.message.reply_text(
            "📖 **Quick User Guide:**\n\n"
            "1️⃣ Deposit Funds: Use UPI (Auto) or Crypto\n"
            "2️⃣ Select Product: Choose Country & Quantity\n"
            "3️⃣ Get OTP: Go to 'My Profile' → 'Orders' → 'Get OTP'\n"
            "4️⃣ Safety: Always use fresh IPs/Proxy",
            parse_mode='Markdown'
        )
    
    elif text == "🆘 Support":
        print("🔍 Calling support...")
        from config.settings import SUPPORT_USERNAME
        await update.message.reply_text(
            f"🆘 **Customer Support:** @{SUPPORT_USERNAME}\n\n"
            f"- Send Payment Proofs\n"
            f"- Report Login Issues\n"
            f"- Bulk Orders\n"
            f"- Account Replacement",
            parse_mode='Markdown'
        )
    
    else:
        # Unknown message
        await update.message.reply_text(
            "Please use the buttons below:",
            reply_markup=main_menu()
        )
