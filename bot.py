import os
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ["BOT_TOKEN"]
PORT = int(os.environ.get("PORT", 8080))
PUBLIC_URL = os.environ.get("RENDER_EXTERNAL_URL")  # Render 部署后会自动注入

# 内存数据（重启会清空；后续可以接数据库/表格）
work_data = {}

def get_keyboard(is_on_break=False):
    if is_on_break:
        return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back")]])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 START WORK", callback_data="start")],
        [InlineKeyboardButton("🚻 BREAK", callback_data="break")],
        [InlineKeyboardButton("🔴 END WORK", callback_data="end")]
    ])

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! Please check in on time:", reply_markup=get_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    name = query.from_user.username or query.from_user.first_name
    now = datetime.datetime.now()

    rec = work_data.setdefault(uid, {"start": None, "end": None, "breaks": [], "break_total": datetime.timedelta()})

    if query.data == "start":
        rec["start"] = now
        rec["end"] = None
        rec["breaks"] = []
        rec["break_total"] = datetime.timedelta()
        await query.edit_message_text(f"🟢 {name} started at {now:%Y-%m-%d %H:%M:%S}", reply_markup=get_keyboard())

    elif query.data == "break":
        rec["breaks"].append({"start": now, "end": None})
        await query.edit_message_text(f"🚻 {name} is on break at {now:%H:%M:%S}", reply_markup=get_keyboard(is_on_break=True))

    elif query.data == "back":
        if rec["breaks"] and rec["breaks"][-1]["end"] is None:
            rec["breaks"][-1]["end"] = now
            rec["break_total"] += rec["breaks"][-1]["end"] - rec["breaks"][-1]["start"]
            await query.edit_message_text(f"🔙 {name} returned at {now:%H:%M:%S}", reply_markup=get_keyboard())
        else:
            await query.edit_message_text("⚠️ No active break found.", reply_markup=get_keyboard())

    elif query.data == "end":
        if not rec["start"]:
            await query.edit_message_text("⚠️ You haven't started work yet.", reply_markup=get_keyboard())
            return
        rec["end"] = now
        net = rec["end"] - rec["start"] - rec["break_total"]
        msg = (
            f"🔴 {name} ended at {now:%Y-%m-%d %H:%M:%S}\n"
            f"🕒 Start: {rec['start']:%Y-%m-%d %H:%M:%S}\n"
            f"🚻 Total break: {rec['break_total']}\n"
            f"✅ Net work: {net}"
        )
        await query.edit_message_text(msg, reply_markup=get_keyboard())

def build_app():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CallbackQueryHandler(button_handler))
    return application

if __name__ == "__main__":
    # Webhook 模式（Render 免费方案推荐）
    app = build_app()
    # 第一次部署时 PUBLIC_URL 还没注入，Render 会在第二次部署后提供该变量
    webhook_url = f"{PUBLIC_URL}/{BOT_TOKEN}" if PUBLIC_URL else None
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=webhook_url,   # 有 PUBLIC_URL 就自动设置 webhook
    )
