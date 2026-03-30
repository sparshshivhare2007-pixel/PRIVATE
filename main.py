import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config.settings import BOT_TOKEN
from bot.handlers.start import start_command
from bot.handlers.menu import handle_message

logging.basicConfig(level=logging.INFO)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 Bot started!")
    app.run_polling()

if __name__ == "__main__":
    main()
