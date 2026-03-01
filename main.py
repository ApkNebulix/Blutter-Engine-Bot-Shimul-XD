import os
import telebot
import subprocess
import shutil
import zipfile
import time
import requests
import urllib.parse
from telebot import types
from pymongo import MongoClient
from datetime import datetime

# --- CONFIGURATION ---
TOKEN = '8635303381:AAH41sv7OVHm7WWAOFzKr3h68Fk0v0j2EvQ' 
ADMIN_ID = 8381570120
LOG_CHANNEL = "@BotControlPanel" 
IMAGE_URL = "https://raw.githubusercontent.com/ApkNebulix/Daroid-AN/refs/heads/main/Img/apknebulix.jpg"
REQUIRED_CHANNELS = ["@ShimulXDModZ"]

bot = telebot.TeleBot(TOKEN)
active_dumps = 0

# --- MONGODB CONNECTION ---
try:
    encoded_pass = urllib.parse.quote_plus("@%aN%#404%App@")
    MONGO_URI = f"mongodb+srv://apknebulix_modz:{encoded_pass}@apknebulix.suopcnt.mongodb.net/?appName=ApkNebulix"
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client['BlutterUltra']
    users_col = db['users']
    banned_col = db['banned']
except Exception as e:
    print(f"DB Error: {e}")

# --- UTILS & LOGGING ---
def send_log(text):
    try: bot.send_message(LOG_CHANNEL, f"🛡 **[SYSTEM LOG]**\n{text}", parse_mode="Markdown")
    except: pass

def is_subscribed(user_id):
    if user_id == ADMIN_ID: return True
    try:
        for ch in REQUIRED_CHANNELS:
            if bot.get_chat_member(ch, user_id).status == 'left': return False
        return True
    except: return True

def get_animation(frame):
    return ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘", "🪐", "🛰", "💎"][frame % 11]

# --- KEYBOARDS ---
def get_verify_markup():
    markup = types.InlineKeyboardMarkup()
    for ch in REQUIRED_CHANNELS:
        markup.add(types.InlineKeyboardButton(f"Join {ch} 📢", url=f"https://t.me/{ch[1:]}"))
    markup.add(types.InlineKeyboardButton("✅ Verify & Continue", callback_data="verify_check"))
    return markup

def get_main_markup(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("👤 Developer", url="https://t.me/ShimulXD")
    btn2 = types.InlineKeyboardButton("🌍 Global Users", callback_data="global_stats")
    markup.add(btn1, btn2)
    if user_id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("⚙️ Admin Control Panel", callback_data="admin_panel"))
    return markup

# --- START COMMAND ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    if banned_col.find_one({"id": uid}): return
    
    # Save User to DB
    if not users_col.find_one({"id": uid}):
        users_col.insert_one({"id": uid, "name": message.from_user.first_name, "username": message.from_user.username})
        send_log(f"New User: {message.from_user.first_name} (`{uid}`)")

    if not is_subscribed(uid):
        bot.send_photo(message.chat.id, IMAGE_URL, 
                       caption="👋 **Welcome to Blutter Pro!**\n\nSecurity check required. Please join our official channel to unlock the engine.",
                       reply_markup=get_verify_markup(), parse_mode="Markdown")
    else:
        show_welcome(message.chat.id, message.from_user.first_name, uid)

def show_welcome(chat_id, name, uid):
    welcome_text = (
        f"🚀 **Hello, {name}!**\n"
        "Welcome to the most advanced Flutter App Dumper.\n\n"
        "🔹 **System:** `v3.0 Premium` ✅\n"
        "🔹 **Status:** `Engine Ready` ⚡\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📥 **Send me your .zip file** to start dumping."
    )
    bot.send_photo(chat_id, IMAGE_URL, caption=welcome_text, reply_markup=get_main_markup(uid), parse_mode="Markdown")

# --- CALLBACK HANDLERS ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    uid = call.from_user.id
    if call.data == "verify_check":
        if is_subscribed(uid):
            bot.delete_message(call.message.chat.id, call.message.message_id)
            show_welcome(call.message.chat.id, call.from_user.first_name, uid)
        else:
            bot.answer_callback_query(call.id, "❌ Join the channel first!", show_alert=True)
            
    elif call.data == "global_stats":
        total = users_col.count_documents({})
        bot.answer_callback_query(call.id, f"🌍 Global Users: {total}", show_alert=True)
        
    elif call.data == "admin_panel" and uid == ADMIN_ID:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📢 Broadcast", callback_data="adm_bc"),
            types.InlineKeyboardButton("🚫 Ban User", callback_data="adm_ban"),
            types.InlineKeyboardButton("✅ Unban User", callback_data="adm_unban"),
            types.InlineKeyboardButton("❌ Close", callback_data="close_msg")
        )
        bot.send_message(call.message.chat.id, "🛡 **Admin Dashboard**\nControl your engine from here.", reply_markup=markup)

    elif call.data == "close_msg":
        bot.delete_message(call.message.chat.id, call.message.message_id)

# --- BROADCAST SYSTEM ---
@bot.callback_query_handler(func=lambda call: call.data == "adm_bc")
def bc_init(call):
    msg = bot.send_message(call.message.chat.id, "📩 Reply to this message with your broadcast content.")
    bot.register_for_reply(msg, broadcast_exec)

def broadcast_exec(message):
    users = users_col.find()
    success = 0
    for u in users:
        try:
            bot.copy_message(u['id'], message.chat.id, message.message_id)
            success += 1
        except: pass
    bot.send_message(ADMIN_ID, f"📢 Broadcast Success: {success}")

# --- DUMPING ENGINE (ADVANCED) ---
@bot.message_handler(content_types=['document'])
def handle_dump(message):
    global active_dumps
    if not is_subscribed(message.from_user.id): return
    if not message.document.file_name.endswith('.zip'): return

    if active_dumps >= 5 and message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⚠️ **Server Load Full!** Please wait 1-2 minutes.")
        return

    active_dumps += 1
    uid = str(message.chat.id)
    work_dir, out_dir = f"work_{uid}", f"out_{uid}"
    shutil.rmtree(work_dir, ignore_errors=True)
    os.makedirs(work_dir)

    status_msg = bot.reply_to(message, "⚙️ **Initializing Engine...**", parse_mode="Markdown")
    send_log(f"User {message.from_user.first_name} started dumping.")

    try:
        # Download
        bot.send_chat_action(message.chat.id, 'typing')
        bot.edit_message_text("🛰 **Downloading File...**", message.chat.id, status_msg.message_id)
        
        file_info = bot.get_file(message.document.file_id)
        url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
        with requests.get(url, stream=True) as r:
            with open(f"{work_dir}/input.zip", 'wb') as f: shutil.copyfileobj(r.raw, f)

        # Extraction
        bot.edit_message_text("📂 **Extracting Assets...**", message.chat.id, status_msg.message_id)
        with zipfile.ZipFile(f"{work_dir}/input.zip", 'r') as z: z.extractall(work_dir)

        # Run Blutter
        if not os.path.exists('blutter_src'):
            subprocess.run("git clone https://github.com/AbhiTheModder/blutter-termux.git blutter_src", shell=True)
        
        os.chdir('blutter_src')
        subprocess.run("find . -type f -exec sed -i 's/std::format/fmt::format/g' {} +", shell=True)
        
        start_t = time.time()
        process = subprocess.Popen(f"python3 blutter.py ../{work_dir} ../{out_dir}", shell=True)
        
        frame = 0
        while process.poll() is None:
            bot.send_chat_action(message.chat.id, 'typing')
            bot.edit_message_text(f"{get_animation(frame)} **Dumping in Progress...**\n`Elapsed: {int(time.time()-start_t)}s` ⏱", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            frame += 1
            time.sleep(3)
        os.chdir('..')

        # Output Handler
        if os.path.exists(out_dir) and any(os.scandir(out_dir)):
            bot.edit_message_text("📤 **Preparing Output...**", message.chat.id, status_msg.message_id)
            res_zip = f"Result_{uid}.zip"
            shutil.make_archive(res_zip.replace('.zip',''), 'zip', out_dir)
            
            bot.send_chat_action(message.chat.id, 'upload_document')
            with open(res_zip, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"✅ **Dump Successful!**\nTime: {int(time.time()-start_t)}s")
            os.remove(res_zip)
            send_log(f"Dump Success for {message.from_user.first_name}")
        else:
            bot.edit_message_text("❌ **Dump Failed!** Missing lib files.", message.chat.id, status_msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"⚠️ Error: `{e}`", message.chat.id, status_msg.message_id)

    finally:
        active_dumps -= 1
        shutil.rmtree(work_dir, ignore_errors=True)
        if os.path.exists(out_dir): shutil.rmtree(out_dir)

# --- RUN ---
send_log("🚀 Bot Started/Restarted on GitHub Actions.")
bot.infinity_polling()
