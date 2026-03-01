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
from datetime import datetime, timedelta

# --- CONFIGURATION ---
TOKEN = '8635303381:AAH41sv7OVHm7WWAOFzKr3h68Fk0v0j2EvQ' # আপনার টোকেন
ADMIN_ID = 8381570120
LOG_CHANNEL = "@BotControlPanel"
REQUIRED_CHANNELS = ["@ShimulXDModZ"]
IMAGE_URL = "https://raw.githubusercontent.com/ApkNebulix/Daroid-AN/refs/heads/main/Img/apknebulix.jpg"

bot = telebot.TeleBot(TOKEN, threaded=True)

# --- DB CONNECTION ---
encoded_pass = urllib.parse.quote_plus("@%aN%#404%App@")
MONGO_URI = f"mongodb+srv://apknebulix_modz:{encoded_pass}@apknebulix.suopcnt.mongodb.net/?appName=ApkNebulix"
client = MongoClient(MONGO_URI)
db = client['BlutterSupreme']
users_col = db['users']
banned_col = db['banned']

# --- GLOBAL STATE ---
CONCURRENCY_LIMIT = 5
active_dumps = 0

# --- HELPER FUNCTIONS ---
def send_log(text):
    try: bot.send_message(LOG_CHANNEL, f"📝 **Log Report:**\n{text}", parse_mode="Markdown")
    except: pass

def is_subscribed(user_id):
    if user_id == ADMIN_ID: return True
    try:
        for ch in REQUIRED_CHANNELS:
            status = bot.get_chat_member(ch, user_id).status
            if status in ['left', 'kicked']: return False
        return True
    except: return True

def get_progress_bar(percent):
    full = int(percent / 10)
    return "🟦" * full + "⬜" * (10 - full) + f" {percent}%"

# --- MIDDLEWARE & UI ---
@bot.message_handler(commands=['start'])
def start_manager(message):
    user = message.from_user
    users_col.update_one({"id": user.id}, {"$set": {"name": user.first_name, "last_active": datetime.now()}}, upsert=True)

    if banned_col.find_one({"id": user.id}):
        return bot.reply_to(message, "🚫 **Access Denied!** You are banned.")

    if not is_subscribed(user.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Join Channel", url="https://t.me/ShimulXDModZ"))
        markup.add(types.InlineKeyboardButton("🔄 Verify Membership", callback_data="verify_user"))
        return bot.send_photo(message.chat.id, IMAGE_URL, caption="⚠️ **Verification Required!**\nPlease join our channel to use this supreme engine.", reply_markup=markup)

    show_welcome(message.chat.id, user.id)

def show_welcome(chat_id, user_id):
    total_users = users_col.count_documents({})
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("👤 Developer", url="https://t.me/ShimulXD")
    btn2 = types.InlineKeyboardButton("📊 Global Stats", callback_data="stats")
    markup.add(btn1, btn2)
    
    if user_id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("⚙️ Admin Control Panel", callback_data="admin_panel"))

    welcome_text = (
        "✨ **WELCOME TO BLUTTER PRO ENGINE** ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 **Bot Status:** `Running 🟢` \n"
        f"👥 **Users Served:** `{total_users}`\n"
        f"🔥 **Load Status:** `{active_dumps}/{CONCURRENCY_LIMIT}`\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📥 **Send me a .zip file** containing\n"
        "`libflutter.so` and `libapp.so` to begin."
    )
    bot.send_photo(chat_id, IMAGE_URL, caption=welcome_text, reply_markup=markup, parse_mode="Markdown")

# --- CALLBACK HANDLERS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    if call.data == "verify_user":
        if is_subscribed(call.from_user.id):
            bot.delete_message(call.message.chat.id, call.message.message_id)
            show_welcome(call.message.chat.id, call.from_user.id)
        else:
            bot.answer_callback_query(call.id, "❌ Please join the channel first!", show_alert=True)

    elif call.data == "stats":
        total = users_col.count_documents({})
        active_10m = users_col.count_documents({"last_active": {"$gt": datetime.now() - timedelta(minutes=10)}})
        bot.answer_callback_query(call.id, f"Total Users: {total}\nActive Now: {active_10m}", show_alert=True)

    elif call.data == "admin_panel":
        if call.from_user.id != ADMIN_ID: return
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Broadcast Message", callback_data="broadcast"))
        markup.add(types.InlineKeyboardButton("🚫 Ban User", callback_data="ban_req"))
        markup.add(types.InlineKeyboardButton("✅ Unban User", callback_data="unban_req"))
        bot.edit_message_caption("🛠 **Supreme Admin Panel**", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data == "broadcast":
        msg = bot.send_message(call.message.chat.id, "💬 **Send the message you want to broadcast:**")
        bot.register_next_step_handler(msg, process_broadcast)

# --- CORE DUMPING LOGIC (ADVANCED) ---
@bot.message_handler(content_types=['document'])
def handle_zip(message):
    global active_dumps
    if not is_subscribed(message.from_user.id): return
    if not message.document.file_name.endswith('.zip'):
        return bot.reply_to(message, "❌ **Error:** Please send a valid `.zip` file.")

    if active_dumps >= CONCURRENCY_LIMIT:
        return bot.reply_to(message, "⚠️ **Server Busy!** Try again in a minute.")

    active_dumps += 1
    uid = str(message.chat.id)
    work_dir = f"work_{uid}"
    out_dir = f"out_{uid}"
    
    # Typing status
    bot.send_chat_action(message.chat.id, 'typing')
    status_msg = bot.reply_to(message, "🌀 **Initializing Supreme Engine...**", parse_mode="Markdown")

    try:
        # Download
        bot.edit_message_text(f"📥 **Status:** `Downloading Files...`\n{get_progress_bar(30)}", message.chat.id, status_msg.message_id, parse_mode="Markdown")
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        os.makedirs(work_dir, exist_ok=True)
        with open(f"{work_dir}/input.zip", 'wb') as f: f.write(downloaded_file)

        # Extraction
        bot.edit_message_text(f"📂 **Status:** `Extracting Data...`\n{get_progress_bar(50)}", message.chat.id, status_msg.message_id, parse_mode="Markdown")
        with zipfile.ZipFile(f"{work_dir}/input.zip", 'r') as z: z.extractall(work_dir)

        # Processing (Blutter)
        bot.edit_message_text(f"⚙️ **Status:** `Running Blutter Engine...`\n`Speed: Optimized 🚀`", message.chat.id, status_msg.message_id, parse_mode="Markdown")
        
        start_time = time.time()
        # GitHub action এ 'blutter_src' ফোল্ডার আগে থেকে থাকলে ভালো, না থাকলে ক্লোন হবে।
        if not os.path.exists('blutter_src'):
            subprocess.run("git clone https://github.com/AbhiTheModder/blutter-termux.git blutter_src", shell=True)
        
        process = subprocess.run(f"python3 blutter_src/blutter.py {work_dir} {out_dir}", shell=True, capture_output=True)

        if os.path.exists(out_dir) and any(os.scandir(out_dir)):
            # Finalizing
            res_zip = f"Dump_{uid}.zip"
            shutil.make_archive(res_zip.replace('.zip',''), 'zip', out_dir)
            
            bot.send_chat_action(message.chat.id, 'upload_document')
            bot.edit_message_text(f"✅ **Dump Success!**\n⏱ Time: {int(time.time()-start_time)}s\n📤 **Uploading...**", message.chat.id, status_msg.message_id)
            
            with open(res_zip, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"💎 **Supreme Dump Completed**\n👤 User: `{message.from_user.first_name}`")
            
            send_log(f"✅ Success: {message.from_user.first_name} ({message.from_user.id})")
            os.remove(res_zip)
        else:
            bot.edit_message_text("❌ **Dump Failed!** Missing library files in ZIP.", message.chat.id, status_msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"⚠️ **Error:** `{str(e)}`", message.chat.id, status_msg.message_id)
        send_log(f"⚠️ Error from {message.from_user.id}: {str(e)}")

    finally:
        active_dumps -= 1
        shutil.rmtree(work_dir, ignore_errors=True)
        shutil.rmtree(out_dir, ignore_errors=True)

# --- ADMIN FUNCTIONS ---
def process_broadcast(message):
    users = users_col.find()
    success = 0
    for u in users:
        try:
            bot.copy_message(u['id'], message.chat.id, message.message_id)
            success += 1
            time.sleep(0.1)
        except: pass
    bot.send_message(ADMIN_ID, f"✅ Broadcast sent to {success} users.")

# --- START BOT ---
print("💎 Supreme Blutter Bot is Live...")
send_log("🚀 **Bot Server is Online**")
bot.infinity_polling()
