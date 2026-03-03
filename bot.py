import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

logging.basicConfig(level=logging.INFO)

telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

# ----------- BASIC START ----------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot is active.")

# ----------- DEBUG GROUP ID ----------- #

async def debug_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    if chat.type in ["group", "supergroup"]:
        print("========== GROUP DETECTED ==========")
        print("Group Name:", chat.title)
        print("REAL GROUP ID:", chat.id)
        print("====================================")

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.ALL, debug_group))

# ----------- FLASK WEBHOOK ----------- #

app = Flask(__name__)

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    await telegram_app.process_update(update)
    return "ok"

@app.route("/")
def index():
    return "Bot is running!"

# ----------- INIT ----------- #

async def init():
    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(f"{WEBHOOK_URL}/{BOT_TOKEN}")

asyncio.get_event_loop().run_until_complete(init())
