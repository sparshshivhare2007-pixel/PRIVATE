from telegram import Update
from telegram.ext import ContextTypes
from bot.handlers.buy_accounts import handle_buy_accounts
from bot.keyboards.main_menu import main_menu

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back to main menu"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "Main Menu:",
        reply_markup=main_menu()
    )

async def back_to_countries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back to countries selection"""
    query = update.callback_query
    await query.answer()
    
    # Re-call buy accounts handler
    from bot.handlers.buy_accounts import handle_buy_accounts
    await handle_buy_accounts(update, context)
    await query.delete_message()
