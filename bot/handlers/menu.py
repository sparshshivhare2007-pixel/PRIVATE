from telegram import Update
from telegram.ext import ContextTypes

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "🛒 Buy Accounts":
        await update.message.reply_text("Coming soon...")
    elif text == "🛍️ Buy Sessions":
        await update.message.reply_text("Coming soon...")
    elif text == "💰 Add Funds":
        await update.message.reply_text("Coming soon...")
    else:
        await update.message.reply_text("Please use the buttons below:")
