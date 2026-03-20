import json
import time
import re
from telegram import *
from telegram.ext import *

TOKEN = "8748637527:AAEVaCOYYhdProEry9IS6ZH46d4FLtOeGrY"

# ---------------- CONFIG ----------------

def load_config():
    try:
        return json.load(open("config.json"))
    except:
        return {}

def save_config(config):
    json.dump(config, open("config.json", "w"), indent=4)

def get_chat_config(chat_id):
    config = load_config()
    chat_id = str(chat_id)

    if chat_id not in config:
        config[chat_id] = {
            "language": "pt",
            "welcome": {
                "enabled": True,
                "text": "👋 Bem-vindo(a), {user}!",
                "image": None
            },
            "auto_moderation": {
                "enabled": True,
                "flood_limit": 5,
                "flood_time": 10,
                "bad_words": ["spam"],
                "anti_link": True
            },
            "punishments": {
                "warn_limit": 3
            }
        }
        save_config(config)

    return config[chat_id]

def update_chat_config(chat_id, new_data):
    config = load_config()
    config[str(chat_id)] = new_data
    save_config(config)

# ---------------- DATABASE ----------------

def load_db():
    try:
        return json.load(open("database.json"))
    except:
        return {"warns": {}, "flood": {}}

def save_db(db):
    json.dump(db, open("database.json", "w"), indent=4)

# ---------------- UTIL ----------------

def get_target(update):
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user.id

    args = update.message.text.split()
    if len(args) > 1:
        try:
            return int(args[1])
        except:
            return None
    return None

async def is_admin(update, context):
    m = await context.bot.get_chat_member(
        update.effective_chat.id,
        update.effective_user.id
    )
    return m.status in ["administrator", "creator"]

# ---------------- COMANDOS ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot estilo Rose ativo!")

async def ban(update, context):
    if not await is_admin(update, context):
        return

    uid = get_target(update)
    if not uid:
        return await update.message.reply_text("Use reply ou ID")

    await context.bot.ban_chat_member(update.effective_chat.id, uid)
    await update.message.reply_text("🚫 Banido")

async def unban(update, context):
    if not await is_admin(update, context):
        return

    uid = get_target(update)
    if not uid:
        return await update.message.reply_text("Use ID do usuário")

    await context.bot.unban_chat_member(
        update.effective_chat.id,
        uid
    )

    await update.message.reply_text("✅ Desbanido")


async def mute(update, context):
    if not await is_admin(update, context):
        return

    uid = get_target(update)
    if not uid:
        return await update.message.reply_text("Use reply ou ID")

    await context.bot.restrict_chat_member(
        update.effective_chat.id,
        uid,
        permissions=ChatPermissions(can_send_messages=False)
    )
    await update.message.reply_text("🔇 Mutado")

async def unmute(update, context):
    if not await is_admin(update, context):
        return

    uid = get_target(update)
    if not uid:
        return await update.message.reply_text("Use reply ou ID")

    await context.bot.restrict_chat_member(
        chat_id=update.effective_chat.id,
        user_id=uid,
        permissions=ChatPermissions(
            can_send_messages=True,
            can_send_audios=True,
            can_send_documents=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_video_notes=True,
            can_send_voice_notes=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_change_info=False,
            can_invite_users=True,
            can_pin_messages=False
        )
    )

    await update.message.reply_text("🔊 Desmutado")

async def warn(update, context):
    if not await is_admin(update, context):
        return

    db = load_db()
    cfg = get_chat_config(update.effective_chat.id)

    uid = get_target(update)
    if not uid:
        return await update.message.reply_text("Use reply ou ID")

    w = db["warns"].get(str(uid), 0) + 1
    db["warns"][str(uid)] = w
    save_db(db)

    await update.message.reply_text(f"⚠️ Warn {w}/{cfg['punishments']['warn_limit']}")

    if w >= cfg["punishments"]["warn_limit"]:
        await context.bot.ban_chat_member(update.effective_chat.id, uid)
        await update.message.reply_text("🚫 Ban automático")

# ---------------- SETTINGS ----------------

async def settings(update, context):
    if not await is_admin(update, context):
        return

    cfg = get_chat_config(update.effective_chat.id)

    kb = [
        [InlineKeyboardButton(f"Welcome: {'ON' if cfg['welcome']['enabled'] else 'OFF'}", callback_data="welcome")],
        [InlineKeyboardButton(f"AntiFlood: {'ON' if cfg['auto_moderation']['enabled'] else 'OFF'}", callback_data="flood")],
        [InlineKeyboardButton(f"AntiLink: {'ON' if cfg['auto_moderation']['anti_link'] else 'OFF'}", callback_data="link")]
    ]

    await update.message.reply_text("⚙️ Settings", reply_markup=InlineKeyboardMarkup(kb))

async def buttons(update, context):
    q = update.callback_query
    await q.answer()

    cfg = get_chat_config(update.effective_chat.id)

    if q.data == "welcome":
        cfg["welcome"]["enabled"] = not cfg["welcome"]["enabled"]

    elif q.data == "flood":
        cfg["auto_moderation"]["enabled"] = not cfg["auto_moderation"]["enabled"]

    elif q.data == "link":
        cfg["auto_moderation"]["anti_link"] = not cfg["auto_moderation"]["anti_link"]

    update_chat_config(update.effective_chat.id, cfg)

    await q.edit_message_text("✅ Atualizado")

# ---------------- WELCOME CONFIG ----------------

async def setwelcome(update, context):
    if not await is_admin(update, context):
        return

    text = update.message.text.replace("/setwelcome ", "")
    cfg = get_chat_config(update.effective_chat.id)

    cfg["welcome"]["text"] = text
    update_chat_config(update.effective_chat.id, cfg)

    await update.message.reply_text("✅ Welcome atualizado!")

async def setwelcomeimg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return

    if not update.message.reply_to_message:
        return await update.message.reply_text("❌ Responda uma imagem")

    msg = update.message.reply_to_message
    file_id = None

    if msg.photo:
        file_id = msg.photo[-1].file_id

    elif msg.document and msg.document.mime_type.startswith("image"):
        file_id = msg.document.file_id

    if not file_id:
        return await update.message.reply_text("❌ Envie uma imagem válida")

    cfg = get_chat_config(update.effective_chat.id)
    cfg["welcome"]["image"] = file_id
    update_chat_config(update.effective_chat.id, cfg)

    await update.message.reply_text("✅ Imagem atualizada!")

async def previewwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = get_chat_config(update.effective_chat.id)

    user = update.effective_user.first_name
    text = cfg["welcome"]["text"].replace("{user}", user)

    try:
        if cfg["welcome"]["image"]:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=cfg["welcome"]["image"],
                caption=text
            )
        else:
            await update.message.reply_text(text)
    except:
        await update.message.reply_text(text)

# ---------------- AUTO MOD ----------------

async def automod(update, context):
    cfg = get_chat_config(update.effective_chat.id)
    db = load_db()

    if not update.message.text:
        return

    msg = update.message.text.lower()
    uid = str(update.message.from_user.id)

    # anti link
    if cfg["auto_moderation"]["anti_link"]:
        if re.search(r"http|t.me|www", msg):
            await update.message.delete()
            await update.message.reply_text("🚫 Links não permitidos")
            return

    # palavras proibidas
    for w in cfg["auto_moderation"]["bad_words"]:
        if w in msg:
            await update.message.delete()
            await update.message.reply_text("🚫 Palavra proibida")
            return

    # flood
    now = time.time()
    data = db["flood"].get(uid, [])
    data = [t for t in data if now - t < cfg["auto_moderation"]["flood_time"]]
    data.append(now)

    db["flood"][uid] = data
    save_db(db)

    if len(data) > cfg["auto_moderation"]["flood_limit"]:
        await update.message.delete()
        await update.message.reply_text("🚫 Flood detectado")

# ---------------- BOAS VINDAS ----------------

async def welcome(update, context):
    cfg = get_chat_config(update.effective_chat.id)

    if not cfg["welcome"]["enabled"]:
        return

    for u in update.message.new_chat_members:
        text = cfg["welcome"]["text"].replace("{user}", u.first_name)

        try:
            if cfg["welcome"]["image"]:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=cfg["welcome"]["image"],
                    caption=text
                )
            else:
                await update.message.reply_text(text)
        except:
            await update.message.reply_text(text)

# ---------------- RUN ----------------

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("ban", ban))
app.add_handler(CommandHandler("unban", unban))
app.add_handler(CommandHandler("unmute", unmute))
app.add_handler(CommandHandler("mute", mute))
app.add_handler(CommandHandler("warn", warn))
app.add_handler(CommandHandler("settings", settings))
app.add_handler(CommandHandler("setwelcome", setwelcome))
app.add_handler(CommandHandler("setwelcomeimg", setwelcomeimg))
app.add_handler(CommandHandler("previewwelcome", previewwelcome))

app.add_handler(CallbackQueryHandler(buttons))

app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, automod))

print("🔥 Bot estilo Rose rodando...")
app.run_polling()
