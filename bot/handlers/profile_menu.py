from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ButtonStyle

def profile_keyboard():
    """Profile menu inline keyboard with colored buttons"""
    keyboard = [
        [
            InlineKeyboardButton(
                "💸 Deposit Now", 
                callback_data="deposit_now",
                style=ButtonStyle.SUCCESS
            )
        ],
        [
            InlineKeyboardButton(
                "📦 My Orders", 
                callback_data="my_orders",
                style=ButtonStyle.DEFAULT
            ),
            InlineKeyboardButton(
                "📋 My Payments", 
                callback_data="my_payments",
                style=ButtonStyle.DEFAULT
            )
        ],
        [
            InlineKeyboardButton(
                "◀️ Back to Menu", 
                callback_data="back_to_menu",
                style=ButtonStyle.DANGER
            )
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
