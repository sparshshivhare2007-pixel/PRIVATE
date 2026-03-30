from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.decorators.admin import admin_only
from database.supabase import db
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

admin_states = {}


@admin_only
async def add_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add new country - /addcountry"""
    await update.message.reply_text(
        "🌍 **Add New Country**\n\nSend me the country name:",
        parse_mode='Markdown'
    )
    admin_states[update.effective_user.id] = {'action': 'waiting_country_name'}


@admin_only
async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add new product - /addproduct"""
    countries = db.fetch_all("SELECT id, name FROM countries WHERE is_active = TRUE ORDER BY name")
    
    if not countries:
        await update.message.reply_text("No countries found. Add a country first using /addcountry")
        return
    
    keyboard = []
    for c in countries:
        keyboard.append([InlineKeyboardButton(f"🌍 {c[1]}", callback_data=f"admin_product_country_{c[0]}")])
    
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="admin_cancel")])
    
    await update.message.reply_text(
        "**Select Country:**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


@admin_only
async def add_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add stock to product - /addstock"""
    products = db.fetch_all("SELECT id, name, country_name, stock FROM products WHERE is_active = TRUE")
    
    if not products:
        await update.message.reply_text("No products found. Add a product first.")
        return
    
    keyboard = []
    for p in products:
        stock_status = f" (Stock: {p[3]})" if p[3] > 0 else " (Out of stock)"
        keyboard.append([InlineKeyboardButton(
            f"📦 {p[1]} - {p[2]}{stock_status}",
            callback_data=f"admin_stock_{p[0]}"
        )])
    
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="admin_cancel")])
    
    await update.message.reply_text(
        "**Select Product to Add Stock:**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


@admin_only
async def list_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all products - /products"""
    products = db.fetch_all("SELECT id, name, price, stock, country_name FROM products")
    
    if not products:
        await update.message.reply_text("No products found. Use /addproduct to add.")
        return
    
    text = "📦 **Products List**\n\n"
    for p in products:
        text += f"📦 **{p[1]}**\n"
        text += f"   🌍 Country: {p[4]}\n"
        text += f"   💰 Price: ₹{p[2]}\n"
        text += f"   📊 Stock: {p[3]}\n"
        text += f"   🆔 ID: `{p[0]}`\n\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')


@admin_only
async def list_countries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all countries - /countries"""
    countries = db.fetch_all("SELECT id, name, flag FROM countries ORDER BY \"order\"")
    
    if not countries:
        await update.message.reply_text("No countries found. Use /addcountry to add.")
        return
    
    text = "🌍 **Countries List**\n\n"
    for i, c in enumerate(countries, 1):
        flag = c[2] if c[2] else "🌍"
        text += f"{i}. {flag} {c[1]} (ID: `{c[0]}`)\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')


@admin_only
async def handle_product_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle product management callbacks"""
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    await query.answer()
    
    if data.startswith("admin_product_country_"):
        country_id = data.replace("admin_product_country_", "")
        admin_states[user_id] = {
            'action': 'waiting_product_details',
            'country_id': country_id
        }
        
        await query.edit_message_text(
            f"**Add Product**\n\nSend product details in this format:\n\n"
            f"`Name: Product Name\nPrice: 100\nYear: 2025\nStock: 10`\n\n"
            f"Example:\n`Name: Telegram Account\nPrice: 70\nYear: 2025\nStock: 50`",
            parse_mode='Markdown'
        )
    
    elif data.startswith("admin_stock_"):
        product_id = data.replace("admin_stock_", "")
        admin_states[user_id] = {
            'action': 'waiting_stock_details',
            'product_id': product_id
        }
        
        await query.edit_message_text(
            f"**Add Stock**\n\nSend accounts in format:\n\n"
            f"`number|password|otp`\n\n"
            f"Example:\n`+919876543210|pass123|123456`\n\n"
            f"Send one per line for multiple accounts.",
            parse_mode='Markdown'
        )
    
    elif data == "admin_cancel":
        admin_states.pop(user_id, None)
        await query.edit_message_text("❌ Operation cancelled.")


@admin_only
async def process_product_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process product details from admin"""
    user_id = update.effective_user.id
    state = admin_states.get(user_id)
    
    if not state or state.get('action') != 'waiting_product_details':
        return False
    
    text = update.message.text.strip()
    
    if text == '/cancel':
        admin_states.pop(user_id, None)
        await update.message.reply_text("❌ Product addition cancelled.")
        return True
    
    try:
        lines = text.split('\n')
        product_data = {}
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                product_data[key.strip().lower()] = value.strip()
        
        name = product_data.get('name')
        price = float(product_data.get('price', 0))
        year = int(product_data.get('year', 2025))
        stock = int(product_data.get('stock', 0))
        country_id = state.get('country_id')
        
        if not name or price <= 0:
            await update.message.reply_text("❌ Invalid format. Use:\nName: Product Name\nPrice: 100\nYear: 2025\nStock: 10")
            return True
        
        # Get country name
        country = db.fetch_one("SELECT name FROM countries WHERE id = %s", (country_id,))
        country_name = country[0] if country else 'Unknown'
        
        # Create product
        db.execute(
            "INSERT INTO products (name, price, year, stock, country_id, country_name, category, is_active, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (name, price, year, stock, country_id, country_name, 'account', True, datetime.now())
        )
        
        await update.message.reply_text(
            f"✅ **Product added successfully!**\n\n"
            f"📦 **Name:** {name}\n"
            f"💰 **Price:** ₹{price}\n"
            f"🌍 **Country:** {country_name}\n"
            f"📊 **Stock:** {stock}\n\n"
            f"Now use `/addstock` to add actual accounts."
        )
        
        admin_states.pop(user_id, None)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
    
    return True


@admin_only
async def process_stock_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process stock details from admin"""
    user_id = update.effective_user.id
    state = admin_states.get(user_id)
    
    if not state or state.get('action') != 'waiting_stock_details':
        return False
    
    product_id = state.get('product_id')
    text = update.message.text.strip()
    
    if text == '/cancel':
        admin_states.pop(user_id, None)
        await update.message.reply_text("❌ Stock addition cancelled.")
        return True
    
    lines = text.split('\n')
    accounts_added = 0
    
    for line in lines:
        line = line.strip()
        if line and '|' in line:
            parts = line.split('|')
            number = parts[0] if len(parts) > 0 else ''
            password = parts[1] if len(parts) > 1 else ''
            otp = parts[2] if len(parts) > 2 else ''
            
            if number:
                db.execute(
                    "INSERT INTO stock (product_id, number, password, otp, is_sold, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                    (product_id, number, password, otp, False, datetime.now())
                )
                accounts_added += 1
    
    if accounts_added > 0:
        # Update product stock count
        new_stock = db.fetch_one("SELECT COUNT(*) FROM stock WHERE product_id = %s AND is_sold = FALSE", (product_id,))
        new_stock_count = new_stock[0] if new_stock else 0
        
        db.execute("UPDATE products SET stock = %s WHERE id = %s", (new_stock_count, product_id))
        
        await update.message.reply_text(
            f"✅ **Stock added successfully!**\n\n"
            f"📱 **Added:** {accounts_added} account(s)\n"
            f"📊 **Total stock now:** {new_stock_count}"
        )
    else:
        await update.message.reply_text("❌ No valid accounts found!")
    
    admin_states.pop(user_id, None)
    return True


@admin_only
async def process_country_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process country name from admin"""
    user_id = update.effective_user.id
    state = admin_states.get(user_id)
    
    if not state or state.get('action') != 'waiting_country_name':
        return False
    
    country_name = update.message.text.strip()
    
    if country_name == '/cancel':
        admin_states.pop(user_id, None)
        await update.message.reply_text("❌ Country addition cancelled.")
        return True
    
    # Check if country already exists
    existing = db.fetch_one("SELECT id FROM countries WHERE name = %s", (country_name,))
    if existing:
        await update.message.reply_text(f"❌ Country '{country_name}' already exists!")
        admin_states.pop(user_id, None)
        return True
    
    # Add country
    count = db.fetch_one("SELECT COUNT(*) FROM countries")
    order = (count[0] + 1) if count else 1
    
    db.execute(
        "INSERT INTO countries (name, code, flag, is_active, \"order\", created_at) VALUES (%s, %s, %s, %s, %s, %s)",
        (country_name, country_name[:2].upper(), "🌍", True, order, datetime.now())
    )
    
    await update.message.reply_text(
        f"✅ **Country added successfully!**\n\n"
        f"🌍 **Name:** {country_name}\n\n"
        f"Now use `/addproduct` to add products.",
        parse_mode='Markdown'
    )
    
    admin_states.pop(user_id, None)
    return True
