import os
import logging
import sqlite3
import uuid
import asyncio
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ---------------- CONFIG ---------------- #

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

QUERY_GROUP_ID = -1003783846840
PAYMENT_GROUP_ID = -1003728874791
TECH_GROUP_ID = -1003747387460
OTHER_GROUP_ID = -1003860208390

# ---------------------------------------- #

logging.basicConfig(level=logging.INFO)

# ---------------- DATABASE ---------------- #

conn = sqlite3.connect("tickets.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id TEXT PRIMARY KEY,
    user_id INTEGER,
    department TEXT,
    status TEXT
)
""")
conn.commit()

DEPARTMENTS = {
    "queries": QUERY_GROUP_ID,
    "payments": PAYMENT_GROUP_ID,
    "tech": TECH_GROUP_ID,
    "others": OTHER_GROUP_ID,
}

user_department = {}

# ---------------- BOT ---------------- #

telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

# ---------------- HANDLERS ---------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🧾 Queries", callback_data="queries")],
        [InlineKeyboardButton("💳 Payment Issues", callback_data="payments")],
        [InlineKeyboardButton("🛠 Technical Support", callback_data="tech")],
        [InlineKeyboardButton("📦 Others", callback_data="others")],
    ]

    await update.message.reply_text(
        "Welcome to TFR Support.\n\nSelect a department:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def department_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_department[query.from_user.id] = query.data
    await query.message.reply_text("Please describe your issue in detail.")

async def receive_issue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id

        if user_id not in user_department:
            await update.message.reply_text("Please type /start first.")
            return

        department = user_department[user_id]
        group_id = DEPARTMENTS[department]

        ticket_id = str(uuid.uuid4())[:8]

        cursor.execute(
            "INSERT INTO tickets VALUES (?, ?, ?, ?)",
            (ticket_id, user_id, department, "open")
        )
        conn.commit()

        await context.bot.send_message(
            chat_id=group_id,
            text=(
                f"🎫 NEW TICKET\n\n"
                f"Ticket ID: #{ticket_id}\n"
                f"User ID: {user_id}\n"
                f"Department: {department.upper()}\n\n"
                f"Issue:\n{update.message.text}\n\n"
                f"/reply {ticket_id} your message\n"
                f"/close {ticket_id}"
            )
        )

        await update.message.reply_text(
            f"✅ Ticket Created\n\n"
            f"A human admin will contact you shortly.\n\n"
            f"Verification Code:\n"
            f"User ID: {user_id}\n"
            f"Ticket ID: #{ticket_id}"
        )

        del user_department[user_id]

    except Exception as e:
        print("ERROR:", e)
        await update.message.reply_text("⚠ Error creating ticket.")

async def reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        return

    ticket_id = context.args[0]
    reply_text = " ".join(context.args[1:])

    cursor.execute("SELECT user_id, status FROM tickets WHERE ticket_id=?", (ticket_id,))
    result = cursor.fetchone()

    if not result:
        return

    user_id, status = result

    if status == "closed":
        return

    await context.bot.send_message(
        chat_id=user_id,
        text=f"📩 Support Reply (Ticket #{ticket_id}):\n\n{reply_text}"
    )

async def close_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        return

    ticket_id = context.args[0]

    cursor.execute("SELECT user_id FROM tickets WHERE ticket_id=?", (ticket_id,))
    result = cursor.fetchone()

    if not result:
        return

    user_id = result[0]

    cursor.execute(
        "UPDATE tickets SET status='closed' WHERE ticket_id=?",
        (ticket_id,)
    )
    conn.commit()

    await context.bot.send_message(
        chat_id=user_id,
        text=f"✅ Your ticket #{ticket_id} has been closed."
    )

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CallbackQueryHandler(department_selected))
telegram_app.add_handler(CommandHandler("reply", reply_command))
telegram_app.add_handler(CommandHandler("close", close_command))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_issue))

# ---------------- FLASK ---------------- #

app = Flask(__name__)

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    await telegram_app.process_update(update)
    return "ok"

@app.route("/")
def index():
    return "Bot is running!"

# ---------------- INIT ---------------- #

async def init():
    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(f"{WEBHOOK_URL}/{BOT_TOKEN}")

asyncio.get_event_loop().run_until_complete(init())
