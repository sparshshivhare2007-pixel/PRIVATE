from telegram import Update
from telegram.ext import ContextTypes
from bot.keyboards.main_menu import main_menu

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Check if user exists in database
    from database.supabase import db
    result = db.fetch_one("SELECT * FROM users WHERE user_id = %s", (user.id,))
    
    if not result:
        # Create new user
        db.execute(
            "INSERT INTO users (user_id, username, first_name) VALUES (%s, %s, %s)",
            (user.id, user.username, user.first_name)
        )
    
    await update.message.reply_text(
        f"🎉 Welcome {user.first_name}!\n\n"
        f"High-Quality Telegram Accounts & Sessions.\n"
        f"Instant Delivery • Auto-Replacement\n\n"
        f"Select a service from the keyboard below:",
        reply_markup=main_menu()
    )
