from telegram import Update
from telegram.ext import ContextTypes
from bot.handlers.buy_accounts import handle_buy_accounts
from bot.keyboards.main_menu import main_menu
import logging

logger = logging.getLogger(__name__)

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back to main menu"""
    query = update.callback_query
    await query.answer()
    
    logger.info(f"User {query.from_user.id} clicked back to menu")
    
    await query.edit_message_text(
        "Main Menu:",
        reply_markup=main_menu()
    )

async def back_to_countries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back to countries selection"""
    query = update.callback_query
    await query.answer()
    
    logger.info(f"User {query.from_user.id} clicked back to countries")
    
    # Re-call buy accounts handler
    await handle_buy_accounts(update, context)
    await query.delete_message()

async def back_to_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back to products list"""
    query = update.callback_query
    await query.answer()
    
    logger.info(f"User {query.from_user.id} clicked back to products")
    
    # Get selected country from context
    country_id = context.user_data.get('selected_country')
    
    if country_id:
        # Simulate country selection again
        from bot.handlers.country_callback import handle_country_callback
        query.data = f"country_{country_id}"
        await handle_country_callback(update, context)
    else:
        await back_to_countries(update, context)
