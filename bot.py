import os
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable not set")

# 存放打卡数据（内存中，重启会丢失；后面可改成数据库或文件持久化）
work_data = {}

def get_keyboard(is_on_break=False):
    if is_on_break:
        return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back")]])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 START WORK", callback_data="start")],
        [InlineKeyboardButton("🚻 Break", callback_data="break")],
        [InlineKeyboardButton("🔴 END WORK", callback_data="end")]
    ])

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! Please check in on time:", reply_markup=get_keyboard())

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    name = query.from_user.username or query.from_user.first_name
    now = datetime.datetime.datetime.now()

    rec = work_data.setdefault(uid, {"start": None, "end": None, "breaks": [], "break_total": datetime.datetime.timedelta()})

    if query.data == "start":
        rec["start"] = now
        rec["end"] = None
        rec["breaks"] = []
        rec["break_total"] = datetime.datetime.timedelta()
        await query.edit_message_text(f"🟢 {name} started at {now.strftime('%Y-%m-%d %H:%M:%S')}", reply_markup=get_keyboard())

    elif query.data == "break":
        rec["breaks"].append({"start": now, "end": None})
        await query.edit_message_text(f"🚻 {name} is on break at {now.strftime('%H:%M:%S')}", reply_markup=get_keyboard(is_on_break=True))

    elif query.data == "back":
        if rec["breaks"] and rec["breaks"][-1]["end"] is None:
            rec["breaks"][-1]["end"] = now
            bstart = rec["breaks"][-1]["start"]
            bend = rec["breaks"][-1]["end"]
            rec["break_total"] += (bend - bstart)
            await query.edit_message_text(f"🔙 {name} returned at {now.strftime('%H:%M:%S')}", reply_markup=get_keyboard())
        else:
            await query.edit_message_text("⚠️ No active break found.", reply_markup=get_keyboard())

    elif query.data == "end":
        if not rec["start"]:
            await query.edit_message_text("⚠️ You haven't started work yet.", reply_markup=get_keyboard())
            return
        rec["end"] = now
        net = rec["end"] - rec["start"] - rec["break_total"]
        msg = (
            f"🔴 {name} ended at {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"🕒 Start: {rec['start'].strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"🚻 Total break: {rec['break_total']}\n"
            f"✅ Net work: {net}"
        )
        await query.edit_message_text(msg, reply_markup=get_keyboard())

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
