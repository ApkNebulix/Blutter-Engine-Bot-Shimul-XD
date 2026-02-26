import os
import telebot
import subprocess
import shutil
import zipfile
import time
import requests
import json
from telebot import types
from pymongo import MongoClient
import urllib.parse

# --- CONFIGURATION ---
TOKEN = '8635303381:AAH41sv7OVHm7WWAOFzKr3h68Fk0v0j2EvQ'
ADMIN_ID = 8381570120
IMAGE_URL = "https://raw.githubusercontent.com/ApkNebulix/Daroid-AN/refs/heads/main/Img/apknebulix.jpg"
REQUIRED_CHANNELS = ["@ShimulXDModZ"]

# --- MONGODB CONNECTION (FIXED ENCODING) ---
# Special characters in password handled correctly
try:
    # pass: @%aN%#404%App@
    encoded_pass = urllib.parse.quote_plus("@%aN%#404%App@")
    MONGO_URI = f"mongodb+srv://apknebulix_modz:{encoded_pass}@apknebulix.suopcnt.mongodb.net/?appName=ApkNebulix"
    
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client['BlutterDB']
    users_col = db['users']
    banned_col = db['banned']
    # Check connection
    client.admin.command('ping')
    print("✅ MongoDB Connected Successfully!")
except Exception as e:
    print(f"❌ MongoDB Connection Error: {e}")

bot = telebot.TeleBot(TOKEN)

# --- DATABASE FUNCTIONS ---
def register_user(user_id, name, username):
    if not users_col.find_one({"id": user_id}):
        users_col.insert_one({
            "id": user_id, 
            "name": name, 
            "username": username,
            "joined_at": time.strftime("%Y-%m-%d")
        })

def is_banned(user_id):
    return banned_col.find_one({"id": user_id}) is not None

# --- UI & HELPERS ---
def create_progress_bar(percent):
    done = int(percent / 10)
    bar = "🟢" * done + "⚪" * (10 - done)
    return f"{bar} {percent}%"

def get_status_animation(frame):
    frames = ["⌛", "⏳", "🛰", "⚡", "💎"]
    return frames[frame % len(frames)]

def is_subscribed(user_id):
    if user_id == ADMIN_ID: return True
    try:
        for channel in REQUIRED_CHANNELS:
            status = bot.get_chat_member(channel, user_id).status
            if status in ['left', 'kicked']: return False
        return True
    except: return True

# --- 413 ERROR FIX (LARGE FILE DOWNLOAD) ---
def download_large_file(file_id, dest):
    file_info = bot.get_file(file_id)
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
    with requests.get(file_url, stream=True) as r:
        r.raise_for_status()
        with open(dest, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return True

# --- ADMIN PANEL ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID: return
    data_count = users_col.count_documents({})
    ban_count = banned_col.count_documents({})
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 Stats", callback_data="stats"),
        types.InlineKeyboardButton("📜 User List", callback_data="user_list"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="bc_info"),
        types.InlineKeyboardButton("❌ Close", callback_data="close_admin")
    )
    
    text = (
        "🛠 **Admin Command Center**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👤 **Admin:** `Shimul XD`\n"
        f"👥 **Total Users:** `{data_count}`\n"
        f"🚫 **Banned:** `{ban_count}`"
    )
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(commands=['userinfo'])
def user_info(message):
    if message.from_user.id != ADMIN_ID: return
    users = users_col.find().limit(50)
    text = "📜 **Bot User List (Last 50):**\n━━━━━━━━━━━━━━━━━━\n"
    for u in users:
        text += f"🔹 `{u['id']}` | {u['name']}\n"
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['ban'])
def ban_cmd(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        target = message.reply_to_message.from_user.id if message.reply_to_message else int(message.text.split()[1])
        if not banned_col.find_one({"id": target}):
            banned_col.insert_one({"id": target})
            bot.reply_to(message, f"✅ User `{target}` banned.")
    except: bot.reply_to(message, "❌ Provide ID or reply to a message.")

@bot.message_handler(commands=['unban'])
def unban_cmd(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        target = int(message.text.split()[1])
        banned_col.delete_one({"id": target})
        bot.reply_to(message, f"✅ User `{target}` unbanned.")
    except: bot.reply_to(message, "❌ Use: `/unban ID`")

@bot.message_handler(commands=['broadcast'])
def bc_cmd(message):
    if message.from_user.id != ADMIN_ID: return
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Reply to a message to broadcast.")
        return
    
    users = users_col.find()
    success, fail = 0, 0
    for u in users:
        try:
            bot.copy_message(u['id'], message.chat.id, message.reply_to_message.message_id)
            success += 1
            time.sleep(0.1)
        except: fail += 1
    bot.send_message(ADMIN_ID, f"📢 **Broadcast Done!**\n✅ Success: {success} | ❌ Fail: {fail}")

# --- CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    if call.data == "verify":
        if is_subscribed(call.from_user.id):
            bot.edit_message_caption("✅ **Verified Successfully!**\nYou can now send files.", call.message.chat.id, call.message.message_id)
        else: bot.answer_callback_query(call.id, "❌ Join channel first!", show_alert=True)
    elif call.data == "stats":
        all_u = users_col.count_documents({})
        bot.answer_callback_query(call.id, f"Total Users: {all_u}", show_alert=True)
    elif call.data == "user_list":
        user_info(call.message)
    elif call.data == "close_admin":
        bot.delete_message(call.message.chat.id, call.message.message_id)

# --- START ---
@bot.message_handler(commands=['start'])
def start(message):
    register_user(message.from_user.id, message.from_user.first_name, message.from_user.username)
    if is_banned(message.from_user.id):
        bot.reply_to(message, "🚫 You are banned.")
        return

    if not is_subscribed(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        for ch in REQUIRED_CHANNELS:
            markup.add(types.InlineKeyboardButton(text="Join Channel 📢", url=f"https://t.me/{ch[1:]}"))
        markup.add(types.InlineKeyboardButton(text="🔄 Verify Membership", callback_data="verify"))
        bot.send_photo(message.chat.id, IMAGE_URL, caption="⚠️ **Access Locked!** Join our channel to use Blutter Pro.", reply_markup=markup)
        return

    welcome_text = (
        "╔════════════════════╗\n"
        "     🚀 **BLUTTER ENGINE PRO**\n"
        "╚════════════════════╝\n"
        "🔹 **Status:** `Online` ✅\n"
        "🔹 **Dev:** @ShimulXD\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📥 Send a `.zip` file with `libflutter.so` and `libapp.so`."
    )
    bot.send_photo(message.chat.id, IMAGE_URL, caption=welcome_text, parse_mode="Markdown")

# --- DUMPING PROCESS (UNCHANGED LOGIC) ---
@bot.message_handler(content_types=['document'])
def handle_docs(message):
    if is_banned(message.from_user.id) or not is_subscribed(message.from_user.id): return
    if not message.document.file_name.endswith('.zip'):
        bot.reply_to(message, "❌ Please send a `.zip` file.")
        return

    uid = str(message.chat.id)
    work_dir, out_dir = f"work_{uid}", f"out_{uid}"
    shutil.rmtree(work_dir, ignore_errors=True)
    os.makedirs(work_dir)

    status = bot.reply_to(message, "🛰 **Initializing...**", parse_mode="Markdown")

    try:
        bot.send_chat_action(message.chat.id, 'typing')
        # 413 Fix Download
        bot.edit_message_text("📥 **Downloading File (No Limit)...**", message.chat.id, status.message_id)
        download_large_file(message.document.file_id, f"{work_dir}/input.zip")

        bot.edit_message_text("📂 **Extracting...**", message.chat.id, status.message_id)
        with zipfile.ZipFile(f"{work_dir}/input.zip", 'r') as z: z.extractall(work_dir)

        if not os.path.exists('blutter_src'):
            subprocess.run("git clone https://github.com/AbhiTheModder/blutter-termux.git blutter_src", shell=True)
        
        os.chdir('blutter_src')
        subprocess.run("find . -type f -exec sed -i 's/std::format/fmt::format/g' {} +", shell=True)
        
        start_t = time.time()
        process = subprocess.Popen(f"python3 blutter.py ../{work_dir} ../{out_dir}", shell=True)
        
        while process.poll() is None:
            bot.send_chat_action(message.chat.id, 'typing')
            elapsed = int(time.time() - start_t)
            bot.edit_message_text(f"{get_status_animation(elapsed)} **Dumping...**\n`Elapsed: {elapsed}s`", 
                                  message.chat.id, status.message_id, parse_mode="Markdown")
            time.sleep(4)
        os.chdir('..')

        if os.path.exists(out_dir) and any(os.scandir(out_dir)):
            res_zip = f"Dump_{uid}.zip"
            shutil.make_archive(res_zip.replace('.zip',''), 'zip', out_dir)
            with open(res_zip, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"✅ **Success!**\nTime: {int(time.time()-start_t)}s")
            os.remove(res_zip)
        else:
            bot.edit_message_text("❌ **Dump Failed.** Check your libs.", message.chat.id, status.message_id)

    except Exception as e:
        bot.edit_message_text(f"⚠️ **Error:** `{e}`", message.chat.id, status.message_id)

    shutil.rmtree(work_dir, ignore_errors=True)
    shutil.rmtree(out_dir, ignore_errors=True)

bot.infinity_polling()
