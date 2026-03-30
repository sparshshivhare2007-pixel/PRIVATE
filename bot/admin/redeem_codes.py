@admin_only
async def create_redeem_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create redeem code - /createcode 50 10"""
    args = context.args
    
    if len(args) < 2:
        await update.message.reply_text("Usage: /createcode <reward> <quantity>")
        return
    
    reward = float(args[0])
    quantity = int(args[1])
    
    codes = []
    for _ in range(quantity):
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        codes.append(code)
        db.execute(
            "INSERT INTO redeem_codes (code, reward, created_by) VALUES (%s, %s, %s)",
            (code, reward, update.effective_user.id)
        )
    
    codes_text = '\n'.join(codes)
    await update.message.reply_text(
        f"✅ Created {quantity} redeem codes worth ₹{reward} each!\n\n"
        f"**Codes:**\n`{codes_text}`\n\n"
        f"Users can redeem with: `/redeem CODE`",
        parse_mode='Markdown'
    )
