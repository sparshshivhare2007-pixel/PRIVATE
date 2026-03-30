from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def profile_keyboard():
    """Profile menu inline keyboard"""
    keyboard = [
        [InlineKeyboardButton("💸 Deposit Now", callback_data="deposit_now")],
        [
            InlineKeyboardButton("📦 My Orders", callback_data="my_orders"),
            InlineKeyboardButton("📋 My Payments", callback_data="my_payments")
        ],
        [InlineKeyboardButton("◀️ Back to Menu", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)
