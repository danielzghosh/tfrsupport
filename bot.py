import os
import logging
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

# ===== GROUP IDS =====
PAYMENTS_GROUP = -1003728874791
QUERIES_GROUP = -1003783846840
OTHERS_GROUP = -1003860208390
TECH_GROUP = -1003747387460
# =====================

app = Flask(__name__)
application = Application.builder().token(BOT_TOKEN).build()


# ---------- HANDLERS ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Payments", callback_data="payments")],
        [InlineKeyboardButton("Queries", callback_data="queries")],
        [InlineKeyboardButton("Others", callback_data="others")],
        [InlineKeyboardButton("Tech", callback_data="tech")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Select a department:",
        reply_markup=reply_markup
    )


async def department_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["department"] = query.data

    await query.message.reply_text("Please describe your issue:")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "department" not in context.user_data:
        return

    department = context.user_data["department"]
    user = update.message.from_user
    text = update.message.text

    ticket_text = (
        f"🎫 NEW TICKET\n\n"
        f"User: {user.full_name}\n"
        f"User ID: {user.id}\n"
        f"Username: @{user.username}\n\n"
        f"Department: {department.upper()}\n\n"
        f"Issue:\n{text}"
    )

    group_id = None

    if department == "payments":
        group_id = PAYMENTS_GROUP
    elif department == "queries":
        group_id = QUERIES_GROUP
    elif department == "others":
        group_id = OTHERS_GROUP
    elif department == "tech":
        group_id = TECH_GROUP

    try:
        await context.bot.send_message(chat_id=group_id, text=ticket_text)
        await update.message.reply_text("✅ Ticket created successfully.")
    except Exception as e:
        logging.error(e)
        await update.message.reply_text("❌ Error creating ticket.")

    context.user_data.clear()


application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(department_selected))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


# ---------- WEBHOOK ROUTE ----------

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return "ok"


# ---------- SET WEBHOOK ON STARTUP ----------

@app.before_first_request
async def setup():
    await application.initialize()
    await application.start()
    await application.bot.set_webhook(f"{WEBHOOK_URL}/{BOT_TOKEN}")
