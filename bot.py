import os
import logging
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

# ===== GROUP IDS =====
PAYMENTS_GROUP = -1003728874791
QUERIES_GROUP = -1003783846840
OTHERS_GROUP = -1003860208390
TECH_GROUP = -1003747387460
# =====================


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

    group_map = {
        "payments": PAYMENTS_GROUP,
        "queries": QUERIES_GROUP,
        "others": OTHERS_GROUP,
        "tech": TECH_GROUP,
    }

    ticket_text = (
        f"🎫 NEW TICKET\n\n"
        f"User: {user.full_name}\n"
        f"User ID: {user.id}\n"
        f"Username: @{user.username}\n\n"
        f"Department: {department.upper()}\n\n"
        f"Issue:\n{text}"
    )

    try:
        await context.bot.send_message(
            chat_id=group_map[department],
            text=ticket_text
        )
        await update.message.reply_text("✅ Ticket created successfully.")
    except Exception as e:
        logging.error(e)
        await update.message.reply_text("❌ Error creating ticket.")

    context.user_data.clear()


def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(department_selected))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()


if __name__ == "__main__":
    main()
