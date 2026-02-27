import os
import telebot
import subprocess
import shutil
import zipfile
import time
import requests
import json
import urllib.parse
from telebot import types
from pymongo import MongoClient
from datetime import datetime, timedelta

# --- 100% PREMIUM CONFIGURATION ---
TOKEN = '8635303381:AAH41sv7OVHm7WWAOFzKr3h68Fk0v0j2EvQ' 
ADMIN_ID = 8381570120
IMAGE_URL = "https://raw.githubusercontent.com/ApkNebulix/Daroid-AN/refs/heads/main/Img/apknebulix.jpg"
REQUIRED_CHANNELS = ["@ShimulXDModZ"]

bot = telebot.TeleBot(TOKEN)

# --- GLOBAL STATE TRACKING ---
CONCURRENCY_LIMIT = 5
active_dumps = 0

# --- MONGODB CONNECTION (REAL-TIME DATA) ---
try:
    encoded_pass = urllib.parse.quote_plus("@%aN%#404%App@")
    MONGO_URI = f"mongodb+srv://apknebulix_modz:{encoded_pass}@apknebulix.suopcnt.mongodb.net/?appName=ApkNebulix"
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client['BlutterSupreme']
    users_col = db['users']
    banned_col = db['banned']
    client.admin.command('ping')
except Exception as e:
    print(f"⚠️ Database Connection Failed: {e}")

# --- DATABASE & REAL-TIME CHECKING ---
def update_user(user):
    """Updates user info and last active timestamp in MongoDB"""
    try:
        users_col.update_one(
            {"id": user.id},
            {"$set": {
                "id": user.id,
                "name": user.first_name,
                "username": user.username,
                "last_active": datetime.now()
            }},
            upsert=True
        )
    except: pass

def get_live_count():
    """Count users active in the last 10 minutes"""
    try:
        ten_mins_ago = datetime.now() - timedelta(minutes=10)
        return users_col.count_documents({"last_active": {"$gt": ten_mins_ago}})
    except: return 0

def is_banned(user_id):
    return banned_col.find_one({"id": user_id}) is not None

def is_subscribed(user_id):
    if user_id == ADMIN_ID: return True
    try:
        for channel in REQUIRED_CHANNELS:
            status = bot.get_chat_member(channel, user_id).status
            if status in ['left', 'kicked']: return False
        return True
    except: return True

# --- PREMIUM UI & ANIMATIONS ---
def get_progress_bar(percent):
    full = int(percent / 10)
    return "🟢" * full + "⚪" * (10 - full) + f" {percent}%"

def get_animation(frame):
    frames = ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘", "🪐", "🛰", "💎", "☄️"]
    return frames[frame % len(frames)]

# --- ANTI-413 UPLOAD/DOWNLOAD LOGIC ---
def download_file_stream(file_id, dest):
    file_info = bot.get_file(file_id)
    url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(dest, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                if chunk: f.write(chunk)
    return True

def upload_catbox(file_path):
    try:
        url = "https://catbox.moe/user/api.php"
        data = {"reqtype": "fileupload"}
        with open(file_path, "rb") as f:
            res = requests.post(url, data=data, files={"fileToUpload": f}, timeout=300)
        return res.text if res.status_code == 200 else None
    except: return None

# --- SUPREME ADMIN CONTROL PANEL ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID: return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🌍 Global State", callback_data="stats"),
        types.InlineKeyboardButton("📜 User Database", callback_data="user_list"),
        types.InlineKeyboardButton("📢 Multi-Broadcast", callback_data="broadcast"),
        types.InlineKeyboardButton("🚫 Ban System", callback_data="ban_panel"),
        types.InlineKeyboardButton("✅ Unban System", callback_data="unban_panel"),
        types.InlineKeyboardButton("❌ Close Panel", callback_data="close")
    )
    bot.send_message(message.chat.id, "💎 **Supreme Admin Command Center**\nSelect a function to execute:", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    update_user(call.from_user)
    if call.data == "stats":
        total = users_col.count_documents({})
        live = get_live_count()
        bot.answer_callback_query(call.id, f"Users: {total} | Live: {live} | Load: {active_dumps}/5", show_alert=True)
    
    elif call.data == "user_list":
        users = users_col.find().limit(50)
        text = "📜 **User Info (Last 50):**\n"
        for u in users: text += f"🔹 `{u['id']}` - {u['name']}\n"
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

    elif call.data == "broadcast":
        msg = bot.send_message(call.message.chat.id, "📢 **Reply to this message** with the content you want to broadcast.")
        bot.register_for_reply(msg, broadcast_handler)

    elif call.data == "verify":
        if is_subscribed(call.from_user.id):
            bot.edit_message_caption("✅ **Verification Success!** Engine Unlocked.", call.message.chat.id, call.message.message_id)
        else: bot.answer_callback_query(call.id, "❌ Join @ShimulXDModZ first!", show_alert=True)

    elif call.data == "close": bot.delete_message(call.message.chat.id, call.message.message_id)

def broadcast_handler(message):
    users = users_col.find()
    success, fail = 0, 0
    for u in users:
        try:
            bot.copy_message(u['id'], message.chat.id, message.message_id)
            success += 1
            time.sleep(0.05)
        except: fail += 1
    bot.send_message(ADMIN_ID, f"✅ **Broadcast Finished!**\nSuccess: {success} | Fail: {fail}")

# --- START & WELCOME SCREEN (SUPREME UI) ---
@bot.message_handler(commands=['start'])
def welcome(message):
    update_user(message.from_user)
    if is_banned(message.from_user.id):
        return bot.reply_to(message, "🚫 **Access Revoked.** You are blacklisted.")

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📢 Channel", url="https://t.me/ShimulXDModZ"),
        types.InlineKeyboardButton("👤 Developer", url="https://t.me/ShimulXD"),
        types.InlineKeyboardButton("🔄 Refresh / Verify", callback_data="verify")
    )

    load_status = f"🟢 Load: {active_dumps}/{CONCURRENCY_LIMIT}" if active_dumps < 4 else f"🔴 Load: {active_dumps}/{CONCURRENCY_LIMIT} (Full)"
    
    welcome_text = (
        "╔════════════════════╗\n"
        "     🚀 **BLUTTER PRO ENGINE**\n"
        "╚════════════════════╝\n"
        f"🔹 **Real-time Status:** `Online` ✅\n"
        f"🔹 **System Load:** {load_status}\n"
        f"🔹 **Live Users:** `{get_live_count()}` 👥\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📥 **How to use:**\n"
        "Send a `.zip` file containing:\n"
        "📂 `libflutter.so` & `libapp.so` \n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💎 **Powered by Blutter Supreme Engine.**"
    )
    bot.send_photo(message.chat.id, IMAGE_URL, caption=welcome_text, reply_markup=markup, parse_mode="Markdown")

# --- CORE DUMPING (SUPREME PERFORMANCE) ---
@bot.message_handler(content_types=['document'])
def start_dump(message):
    global active_dumps
    user_id = message.from_user.id
    update_user(message.from_user)

    if is_banned(user_id): return
    if not is_subscribed(user_id):
        return bot.reply_to(message, "⚠️ **Security Check:** Join @ShimulXDModZ to unlock.")

    # Concurrency Check
    if active_dumps >= CONCURRENCY_LIMIT and user_id != ADMIN_ID:
        return bot.reply_to(message, "🚫 **Server Busy!**\nMaximum 5 users are dumping. Try again in 60 seconds.")

    if not message.document.file_name.endswith('.zip'):
        return bot.reply_to(message, "❌ **Format Error:** Please send a `.zip` archive.")

    active_dumps += 1
    uid = str(message.chat.id)
    work_dir, out_dir = f"work_{uid}", f"out_{uid}"
    shutil.rmtree(work_dir, ignore_errors=True)
    os.makedirs(work_dir)

    status_msg = bot.reply_to(message, "🛰 **Initializing Supreme Engine...**", parse_mode="Markdown")

    try:
        # Step 1: Downloading Status
        bot.send_chat_action(message.chat.id, 'typing')
        for i in range(10, 101, 30):
            bot.edit_message_text(f"{get_animation(i)} **Status:** `Downloading...`\n{get_progress_bar(i)}", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            time.sleep(0.4)
        
        download_file_stream(message.document.file_id, f"{work_dir}/input.zip")

        # Step 2: Extraction Status
        bot.send_chat_action(message.chat.id, 'typing')
        bot.edit_message_text("📂 **Status:** `Extracting Metadata...`\n`Speed: 1.2 GB/s` ⚡", message.chat.id, status_msg.message_id, parse_mode="Markdown")
        with zipfile.ZipFile(f"{work_dir}/input.zip", 'r') as z: z.extractall(work_dir)

        # Step 3: Dumping (Real-time Progress)
        if not os.path.exists('blutter_src'):
            subprocess.run("git clone https://github.com/AbhiTheModder/blutter-termux.git blutter_src", shell=True)
        
        os.chdir('blutter_src')
        subprocess.run("find . -type f -exec sed -i 's/std::format/fmt::format/g' {} +", shell=True)
        
        start_t = time.time()
        process = subprocess.Popen(f"python3 blutter.py ../{work_dir} ../{out_dir}", shell=True)
        
        frame = 0
        while process.poll() is None:
            bot.send_chat_action(message.chat.id, 'typing')
            elapsed = int(time.time() - start_t)
            bot.edit_message_text(f"{get_animation(frame)} **Status:** `Dumping Core...`\n`Time Elapsed: {elapsed}s` ⏱\n`Thread: Real-time C++ Compilation` ⚙️", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            frame += 1
            time.sleep(3)
        os.chdir('..')

        # Step 4: Finalizing & Uploading Status
        if os.path.exists(out_dir) and any(os.scandir(out_dir)):
            res_zip = f"Supreme_Dump_{uid}.zip"
            shutil.make_archive(res_zip.replace('.zip',''), 'zip', out_dir)
            f_size = os.path.getsize(res_zip) / (1024 * 1024)

            if f_size > 49.0:
                bot.send_chat_action(message.chat.id, 'typing')
                bot.edit_message_text(f"☁️ **Status:** `Uploading to Cloud (Large File: {f_size:.1f}MB)`", message.chat.id, status_msg.message_id)
                link = upload_catbox(res_zip)
                if link:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("📥 Download Supreme Result", url=link))
                    bot.send_message(message.chat.id, f"✅ **Dumping Complete!**\nTime: {int(time.time()-start_t)}s", reply_markup=markup, parse_mode="Markdown")
                else: bot.edit_message_text("❌ **Upload Failed.** Cloud server timeout.", message.chat.id, status_msg.message_id)
            else:
                bot.send_chat_action(message.chat.id, 'upload_document')
                bot.edit_message_text("📤 **Status:** `Sending to Telegram...`", message.chat.id, status_msg.message_id)
                with open(res_zip, 'rb') as f:
                    bot.send_document(message.chat.id, f, caption=f"✅ **Dump Successful!**\n⏱ Time: {int(time.time()-start_t)}s")
            
            os.remove(res_zip)
        else: bot.edit_message_text("❌ **Dump Failed!** Library files are missing or corrupt.", message.chat.id, status_msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"⚠️ **Supreme Error:** `{e}`", message.chat.id, status_msg.message_id)

    finally:
        active_dumps -= 1 # Slots released
        shutil.rmtree(work_dir, ignore_errors=True)
        if os.path.exists(out_dir): shutil.rmtree(out_dir)

# --- SUPREME POLLING ---
print("💎 Supreme Blutter Bot Started...")
bot.infinity_polling(timeout=90, long_polling_timeout=90)
