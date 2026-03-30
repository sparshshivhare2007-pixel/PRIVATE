import logging
import asyncio
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config.settings import BOT_TOKEN

# ================= USER HANDLERS =================
from bot.handlers.start import start_command
from bot.handlers.menu import handle_message
from bot.handlers.buy_accounts import handle_buy_accounts
from bot.handlers.buy_sessions import (
    handle_buy_sessions,
    handle_session_country_callback,
    handle_session_product_callback,
    handle_session_confirm_callback,
)
from bot.handlers.country_callback import handle_country_callback
from bot.handlers.product_callback import handle_product_callback
from bot.handlers.profile import handle_my_profile
from bot.handlers.profile_callbacks import handle_profile_callbacks
from bot.handlers.back_handlers import (
    back_to_menu,
    back_to_countries,
    back_to_products,
    back_to_session_countries,
    back_to_session_products,
)

# ================= ADD FUNDS =================
from bot.handlers.add_funds import (
    handle_add_funds,
    handle_payment_callback,
    handle_utr_message,
    handle_amount_message,
    handle_crypto_proof,
    handle_admin_verify,
)

# ================= EARN MONEY =================
from bot.handlers.earn_money import (
    handle_earn_money,
    handle_redeem_command,
    handle_copy_referral_link,
)

# ================= ADMIN =================
from bot.admin.redeem_codes import (
    create_redeem_code,
    list_active_codes,
    list_used_codes,
    disable_code,
    enable_code,
    code_stats,
    create_bulk_codes,
    process_bulk_codes,
)

from bot.admin.product_commands import (
    add_country,
    add_product,
    add_stock,
    list_products,
    list_countries,
    handle_product_callback as admin_product_callback,
    process_product_details,
    process_stock_details,
    process_country_name,
)

# ✅ LOGIN SYSTEM (NEW ROUTER)
from bot.admin.login import (
    admin_login,
    handle_login_country,
    cancel_login,
    login_router,
    close_telethon_client,
)

logging.basicConfig(level=logging.INFO)


# ================= CLEAN SHUTDOWN =================
async def shutdown():
    print("\n🔄 Shutting down gracefully...")
    try:
        await close_telethon_client()
        print("✅ Telethon closed")
    except Exception as e:
        print(f"⚠️ Shutdown error: {e}")

    print("✅ Bot stopped")


# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # =================================================
    # COMMAND HANDLERS
    # =================================================
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("redeem", handle_redeem_command))

    # ===== ADMIN PRODUCTS =====
    app.add_handler(CommandHandler("addcountry", add_country))
    app.add_handler(CommandHandler("addproduct", add_product))
    app.add_handler(CommandHandler("addstock", add_stock))
    app.add_handler(CommandHandler("products", list_products))
    app.add_handler(CommandHandler("countries", list_countries))

    # ===== ADMIN CODES =====
    app.add_handler(CommandHandler("createcode", create_redeem_code))
    app.add_handler(CommandHandler("codes", list_active_codes))
    app.add_handler(CommandHandler("usedcodes", list_used_codes))
    app.add_handler(CommandHandler("disablecode", disable_code))
    app.add_handler(CommandHandler("enablecode", enable_code))
    app.add_handler(CommandHandler("codestats", code_stats))
    app.add_handler(CommandHandler("bulkcodes", create_bulk_codes))

    # ===== ADMIN LOGIN =====
    app.add_handler(CommandHandler("login", admin_login))

    # =================================================
    # MESSAGE HANDLERS (VERY IMPORTANT ORDER)
    # =================================================

    # ✅ LOGIN ROUTER (FIRST PRIORITY)
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, login_router),
        group=0,
    )

    # ✅ ADD FUNDS FLOW
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_utr_message),
        group=1,
    )
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount_message),
        group=1,
    )
    app.add_handler(
        MessageHandler(filters.PHOTO, handle_crypto_proof),
        group=1,
    )

    # ✅ ADMIN PRODUCT INPUTS
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, process_product_details),
        group=2,
    )
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, process_stock_details),
        group=2,
    )
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, process_country_name),
        group=2,
    )
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, process_bulk_codes),
        group=2,
    )

    # ✅ MAIN MENU (LAST CATCH ALL)
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message),
        group=99,
    )

    # =================================================
    # CALLBACK HANDLERS
    # =================================================

    # Accounts
    app.add_handler(CallbackQueryHandler(handle_country_callback, pattern="^country_"))
    app.add_handler(CallbackQueryHandler(handle_product_callback, pattern="^product_"))
    app.add_handler(CallbackQueryHandler(handle_product_callback, pattern="^confirm_purchase_"))

    # Sessions
    app.add_handler(
        CallbackQueryHandler(handle_session_country_callback, pattern="^session_country_")
    )
    app.add_handler(
        CallbackQueryHandler(handle_session_product_callback, pattern="^session_product_")
    )
    app.add_handler(
        CallbackQueryHandler(handle_session_confirm_callback, pattern="^session_confirm_")
    )

    # Profile
    app.add_handler(
        CallbackQueryHandler(
            handle_profile_callbacks,
            pattern="^(deposit_now|my_orders|my_payments)$",
        )
    )

    # Payments
    app.add_handler(CallbackQueryHandler(handle_payment_callback, pattern="^pay_"))
    app.add_handler(CallbackQueryHandler(handle_admin_verify, pattern="^(verify|reject)_"))

    # Earn money
    app.add_handler(
        CallbackQueryHandler(handle_copy_referral_link, pattern="^copy_referral_link$")
    )

    # Admin product callbacks
    app.add_handler(CallbackQueryHandler(admin_product_callback, pattern="^admin_"))

    # Login callbacks
    app.add_handler(
        CallbackQueryHandler(handle_login_country, pattern="^login_country_")
    )
    app.add_handler(
        CallbackQueryHandler(cancel_login, pattern="^cancel_login$")
    )

    # Back buttons
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$"))
    app.add_handler(CallbackQueryHandler(back_to_countries, pattern="^back_to_countries$"))
    app.add_handler(CallbackQueryHandler(back_to_products, pattern="^back_to_products$"))
    app.add_handler(
        CallbackQueryHandler(back_to_session_countries, pattern="^back_to_session_countries$")
    )
    app.add_handler(
        CallbackQueryHandler(back_to_session_products, pattern="^back_to_session_products$")
    )

    # =================================================
    print("=" * 50)
    print("🤖 Telegram Store Bot Started!")
    print("✅ Bot running...")
    print("Press CTRL+C to stop")
    print("=" * 50)

    try:
        app.run_polling()
    finally:
        asyncio.run(shutdown())


if __name__ == "__main__":
    main()
