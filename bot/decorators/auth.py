from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from database.supabase import db
import logging

logger = logging.getLogger(__name__)

def check_user(func):
    """Decorator to check if user exists in database"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        username = update.effective_user.username
        first_name = update.effective_user.first_name
        
        # Check if user exists
        user = db.fetch_one("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
        
        if not user:
            # Create new user
            db.execute(
                "INSERT INTO users (user_id, username, first_name, balance, total_deposit, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                (user_id, username, first_name, 0, 0, datetime.now())
            )
            logger.info(f"New user created: {user_id}")
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


def check_verified(func):
    """Decorator to check if user is verified"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        user = db.fetch_one("SELECT fsub_verified FROM users WHERE user_id = %s", (user_id,))
        
        if not user or not user[0]:
            if update.message:
                await update.message.reply_text(
                    "⚠️ Please verify your membership first.\n\n"
                    "Join our channel and try again."
                )
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


def check_not_banned(func):
    """Decorator to check if user is not banned"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        user = db.fetch_one("SELECT is_banned FROM users WHERE user_id = %s", (user_id,))
        
        if user and user[0]:
            if update.message:
                await update.message.reply_text("❌ You are banned from using this bot.")
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper
