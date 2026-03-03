import os
import logging
import sqlite3
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

QUERY_GROUP_ID = -5212355257
PAYMENT_GROUP_ID = -4632730127
TECH_GROUP_ID = -5129927362
OTHER_GROUP_ID = -1003860208390

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

user_state = {}

# ---------------- BOT LOGIC ---------------- #

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

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_state[query.from_user.id] = query.data

    await query.message.reply_text("Please describe your issue in detail.")

async def receive_issue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id not in user_state:
        await update.message.reply_text("Please type /start first.")
        return

    department = user_state[user_id]
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
        f"A human admin from TFR_Support will contact you shortly.\n\n"
        f"Verification Code:\n"
        f"User ID: {user_id}\n"
        f"Ticket ID: #{ticket_id}"
    )

    del user_state[user_id]

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

# ---------------- MAIN ---------------- #

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_click))
app.add_handler(CommandHandler("reply", reply_command))
app.add_handler(CommandHandler("close", close_command))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_issue))

if __name__ == "__main__":
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        webhook_url=WEBHOOK_URL,
    )
