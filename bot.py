import os
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ["BOT_TOKEN"]
PORT = int(os.environ.get("PORT", 8080))
PUBLIC_URL = os.environ.get("RENDER_EXTERNAL_URL")  # Render 会自动注入

work_data = {}

def kb(on_break=False):
    if on_break:
        return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back")]])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 START WORK", callback_data="start")],
        [InlineKeyboardButton("🚻 BREAK", callback_data="break")],
        [InlineKeyboardButton("🔴 END WORK", callback_data="end")]
    ])

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! Please check in on time:", reply_markup=kb())

async def btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    name = q.from_user.username or q.from_user.first_name
    now = datetime.datetime.now()
    rec = work_data.setdefault(uid, {"start": None, "end": None, "breaks": [], "break_total": datetime.timedelta()})

    if q.data == "start":
        rec["start"] = now
        rec["end"] = None
        rec["breaks"] = []
        rec["break_total"] = datetime.timedelta()
        await q.edit_message_text(f"🟢 {name} started at {now:%Y-%m-%d %H:%M:%S}", reply_markup=kb())

    elif q.data == "break":
        rec["breaks"].append({"start": now, "end": None})
        await q.edit_message_text(f"🚻 {name} is on break at {now:%H:%M:%S}", reply_markup=kb(on_break=True))

    elif q.data == "back":
        if rec["breaks"] and rec["breaks"][-1]["end"] is None:
            rec["breaks"][-1]["end"] = now
            rec["break_total"] += rec["breaks"][-1]["end"] - rec["breaks"][-1]["start"]
            await q.edit_message_text(f"🔙 {name} returned at {now:%H:%M:%S}", reply_markup=kb())
        else:
            await q.edit_message_text("⚠️ No active break found.", reply_markup=kb())

    elif q.data == "end":
        if not rec["start"]:
            await q.edit_message_text("⚠️ You haven't started work yet.", reply_markup=kb())
            return
        rec["end"] = now
        net = rec["end"] - rec["start"] - rec["break_total"]
        msg = (
            f"🔴 {name} ended at {now:%Y-%m-%d %H:%M:%S}\n"
            f"🕒 Start: {rec['start']:%Y-%m-%d %H:%M:%S}\n"
            f"🚻 Total break: {rec['break_total']}\n"
            f"✅ Net work: {net}"
        )
        await q.edit_message_text(msg, reply_markup=kb())

def build_app():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CallbackQueryHandler(btn))
    return app

if __name__ == "__main__":
    app = build_app()
    webhook_url = f"{PUBLIC_URL}/{BOT_TOKEN}" if PUBLIC_URL else None
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=webhook_url,
    )
