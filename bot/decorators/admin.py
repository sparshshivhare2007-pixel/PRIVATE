from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from config.settings import ADMIN_IDS
import logging

logger = logging.getLogger(__name__)

def admin_only(func):
    """Decorator to restrict access to admins only"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        if user_id not in ADMIN_IDS:
            # For message updates
            if update.message:
                await update.message.reply_text("⛔ You are not authorized to use this command.")
            # For callback queries
            elif update.callback_query:
                await update.callback_query.answer("⛔ Unauthorized", show_alert=True)
            
            logger.warning(f"Unauthorized admin access attempt by {user_id}")
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper
