from telegram import ReplyKeyboardMarkup

def main_menu():
    keyboard = [
        ["🛒 Buy Accounts", "🛍️ Buy Sessions"],
        ["💰 Add Funds", "💵 Earn Money"],
        ["👤 My Profile", "❓ How to Use"],
        ["🆘 Support"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
