import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
BOT_USERNAME = os.getenv('BOT_USERNAME')
DATABASE_URL = os.getenv('DATABASE_URL')
ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id]
UPDATE_CHANNEL = os.getenv('UPDATE_CHANNEL')
LOGS_CHANNEL = os.getenv('LOGS_CHANNEL')
UPI_ID = os.getenv('UPI_ID')
BINANCE_PAY_ID = os.getenv('BINANCE_PAY_ID')
USDT_ADDRESS = os.getenv('USDT_ADDRESS')
