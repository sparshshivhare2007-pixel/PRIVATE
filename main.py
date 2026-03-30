import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config.settings import BOT_TOKEN
from bot.handlers.start import start_command
from bot.handlers.menu import handle_message
from bot.handlers.buy_accounts import handle_buy_accounts
from bot.handlers.country_callback import handle_country_callback
from bot.handlers.back_handlers import back_to_menu, back_to_countries, back_to_products
from bot.handlers.product_callback import handle_product_callback
from bot.handlers.profile import handle_my_profile
from bot.handlers.profile_callbacks import handle_profile_callbacks

logging.basicConfig(level=logging.INFO)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # ============== COMMAND HANDLERS ==============
    app.add_handler(CommandHandler("start", start_command))
    
    # ============== MESSAGE HANDLERS ==============
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # ============== CALLBACK QUERY HANDLERS ==============
    # Country selection
    app.add_handler(CallbackQueryHandler(handle_country_callback, pattern="^country_"))
    
    # Product selection
    app.add_handler(CallbackQueryHandler(handle_product_callback, pattern="^product_"))
    
    # Profile buttons
    app.add_handler(CallbackQueryHandler(handle_profile_callbacks, pattern="^(deposit_now|my_orders|my_payments)$"))
    
    # Back buttons
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$"))
    app.add_handler(CallbackQueryHandler(back_to_countries, pattern="^back_to_countries$"))
    app.add_handler(CallbackQueryHandler(back_to_products, pattern="^back_to_products$"))
    
    print("="*50)
    print("🤖 Telegram Store Bot Started!")
    print("="*50)
    print("✅ Bot is running...")
    print("📊 Press Ctrl+C to stop")
    print("="*50)
    
    app.run_polling()

if __name__ == "__main__":
    main()
