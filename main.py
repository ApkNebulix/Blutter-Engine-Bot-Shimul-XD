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

# --- MONGODB CONNECTION (SECURE ENCODING) ---
try:
    encoded_pass = urllib.parse.quote_plus("@%aN%#404%App@")
    MONGO_URI = f"mongodb+srv://apknebulix_modz:{encoded_pass}@apknebulix.suopcnt.mongodb.net/?appName=ApkNebulix"
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client['BlutterDB']
    users_col = db['users']
    banned_col = db['banned']
    client.admin.command('ping')
    print("✅ MongoDB Connected!")
except Exception as e:
    print(f"❌ MongoDB Error: {e}")

bot = telebot.TeleBot(TOKEN)

# --- DATABASE FUNCTIONS ---
def register_user(user):
    if not users_col.find_one({"id": user.id}):
        users_col.insert_one({
            "id": user.id,
            "name": user.first_name,
            "username": user.username,
            "joined_date": time.strftime("%Y-%m-%d %H:%M:%S")
        })

def is_banned(user_id):
    return banned_col.find_one({"id": user_id}) is not None

# --- UI & ANIMATION HELPERS (UNCHANGED) ---
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

# --- 413 ERROR FIX (LARGE FILE HANDLER) ---
def download_large_file(file_id, dest):
    file_info = bot.get_file(file_id)
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
    with requests.get(file_url, stream=True) as r:
        r.raise_for_status()
        with open(dest, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return True

# --- ADMIN PANEL (FULL BUTTON SYSTEM) ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID: return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 Stats", callback_data="adm_stats"),
        types.InlineKeyboardButton("📜 User List", callback_data="adm_users"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="adm_bc"),
        types.InlineKeyboardButton("🚫 Ban User", callback_data="adm_ban"),
        types.InlineKeyboardButton("✅ Unban User", callback_data="adm_unban"),
        types.InlineKeyboardButton("❌ Close Panel", callback_data="adm_close")
    )
    
    total_u = users_col.count_documents({})
    ban_u = banned_col.count_documents({})
    
    admin_text = (
        "🛠 **ADMIN COMMAND CENTER**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👤 **Admin:** `Shimul XD`\n"
        f"👥 **Total Registered:** `{total_u}`\n"
        f"🚫 **Banned Users:** `{ban_u}`\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Select an action from the buttons below:"
    )
    bot.send_message(message.chat.id, admin_text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
def admin_callbacks(call):
    if call.from_user.id != ADMIN_ID: return
    
    if call.data == "adm_stats":
        total_u = users_col.count_documents({})
        ban_u = banned_col.count_documents({})
        bot.answer_callback_query(call.id, f"Total Users: {total_u}\nBanned: {ban_u}", show_alert=True)
    
    elif call.data == "adm_users":
        users = users_col.find().limit(50)
        user_text = "📜 **User List (Last 50):**\n━━━━━━━━━━━━\n"
        for u in users:
            user_text += f"🔹 `{u['id']}` | {u['name']}\n"
        bot.send_message(call.message.chat.id, user_text, parse_mode="Markdown")

    elif call.data == "adm_bc":
        msg = bot.send_message(call.message.chat.id, "📩 **Reply to this message** with the Content (Text/Photo) you want to broadcast.")
        bot.register_for_reply(msg, broadcast_handler)

    elif call.data == "adm_ban":
        msg = bot.send_message(call.message.chat.id, "🆔 Enter the **User ID** you want to ban:")
        bot.register_next_step_handler(msg, ban_handler)

    elif call.data == "adm_unban":
        msg = bot.send_message(call.message.chat.id, "🆔 Enter the **User ID** you want to unban:")
        bot.register_next_step_handler(msg, unban_handler)

    elif call.data == "adm_close":
        bot.delete_message(call.message.chat.id, call.message.message_id)

# Admin Handlers
def broadcast_handler(message):
    users = users_col.find()
    success, fail = 0, 0
    for u in users:
        try:
            bot.copy_message(u['id'], message.chat.id, message.message_id)
            success += 1
            time.sleep(0.05)
        except: fail += 1
    bot.send_message(ADMIN_ID, f"📢 **Broadcast Complete!**\n✅ Success: {success} | ❌ Fail: {fail}")

def ban_handler(message):
    try:
        uid = int(message.text)
        if not banned_col.find_one({"id": uid}):
            banned_col.insert_one({"id": uid})
            bot.send_message(ADMIN_ID, f"✅ User `{uid}` banned.")
    except: bot.send_message(ADMIN_ID, "❌ Invalid ID.")

def unban_handler(message):
    try:
        uid = int(message.text)
        banned_col.delete_one({"id": uid})
        bot.send_message(ADMIN_ID, f"✅ User `{uid}` unbanned.")
    except: bot.send_message(ADMIN_ID, "❌ Invalid ID.")

# --- START & WELCOME (UNCHANGED DESIGN) ---
@bot.message_handler(commands=['start'])
def welcome(message):
    register_user(message.from_user.id, message.from_user) if False else register_user(message.from_user)
    
    if is_banned(message.from_user.id):
        bot.reply_to(message, "🚫 **Access Denied!** You are banned.")
        return

    if not is_subscribed(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        for ch in REQUIRED_CHANNELS:
            markup.add(types.InlineKeyboardButton(text="Join Channel 📢", url=f"https://t.me/{ch[1:]}"))
        markup.add(types.InlineKeyboardButton(text="🔄 Verify Membership", callback_data="verify"))
        
        bot.send_photo(message.chat.id, IMAGE_URL, 
                       caption=f"👋 **Hello {message.from_user.first_name}!**\n\n⚠️ **Access Locked:**\nYou must join our official channels to use the **Blutter Pro Engine**.",
                       parse_mode="Markdown", reply_markup=markup)
        return

    welcome_text = (
        "╔════════════════════╗\n"
        "     🚀 **BLUTTER ENGINE PRO**\n"
        "╚════════════════════╝\n"
        "🔹 **Status:** `Online / Ready` ✅\n"
        "🔹 **Version:** `v2.5 High-Speed` ⚡\n"
        "🔹 **Dev:** @ShimulXD\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📥 **How to use:**\n"
        "Send a `.zip` file containing:\n"
        "📂 `libflutter.so` & `libapp.so` \n"
        "━━━━━━━━━━━━━━━━━━\n"
        "✨ **Features:** Auto-sed, C++ Core Dumping, High Compression Output."
    )
    bot.send_photo(message.chat.id, IMAGE_URL, caption=welcome_text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "verify")
def verify_btn(call):
    if is_subscribed(call.from_user.id):
        bot.edit_message_caption("✅ **Verified Successfully!**\nYou can now send your zip files for dumping.", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ Join the channel first!", show_alert=True)

# --- CORE DUMPING (ALL ANIMATIONS UNCHANGED) ---
@bot.message_handler(content_types=['document'])
def handle_dump(message):
    if is_banned(message.from_user.id) or not is_subscribed(message.from_user.id): return

    if not message.document.file_name.endswith('.zip'):
        bot.reply_to(message, "❌ **Error:** Send a `.zip` file.")
        return

    uid = str(message.chat.id)
    work_dir, out_dir = f"work_{uid}", f"out_{uid}"
    shutil.rmtree(work_dir, ignore_errors=True)
    os.makedirs(work_dir)

    status_msg = bot.reply_to(message, "🛰 **Initializing Engine...**", parse_mode="Markdown")

    try:
        # Download (Fix 413)
        for i in range(10, 101, 30):
            bot.edit_message_text(f"{get_status_animation(i//25)} **Downloading File...**\n{create_progress_bar(i)}", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            time.sleep(0.3)
        
        success = download_large_file(message.document.file_id, f"{work_dir}/input.zip")
        if not success: raise Exception("Failed to download large file.")

        # Extract
        bot.edit_message_text("📂 **Extracting Resources...**\n`Analyzing Bytecode...` ⚡", 
                              message.chat.id, status_msg.message_id, parse_mode="Markdown")
        with zipfile.ZipFile(f"{work_dir}/input.zip", 'r') as z: z.extractall(work_dir)

        # Engine Run
        if not os.path.exists('blutter_src'):
            subprocess.run("git clone https://github.com/AbhiTheModder/blutter-termux.git blutter_src", shell=True)
        
        os.chdir('blutter_src')
        subprocess.run("find . -type f -exec sed -i 's/std::format/fmt::format/g' {} +", shell=True)
        
        start_t = time.time()
        process = subprocess.Popen(f"python3 blutter.py ../{work_dir} ../{out_dir}", shell=True)
        
        while process.poll() is None:
            bot.send_chat_action(message.chat.id, 'typing')
            elapsed = int(time.time() - start_t)
            ani = get_status_animation(elapsed)
            bot.edit_message_text(f"{ani} **Dumping in Progress...**\n`Elapsed Time: {elapsed}s` ⏱\n`Status: Compiling C++ Core` 🛠", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            time.sleep(4)
        os.chdir('..')

        # Finalize
        if os.path.exists(out_dir) and any(os.scandir(out_dir)):
            res_zip = f"Blutter_Output_{uid}.zip"
            shutil.make_archive(res_zip.replace('.zip',''), 'zip', out_dir)
            with open(res_zip, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"✅ **Dump Success!**\n⏱ **Time Taken:** {int(time.time()-start_t)}s\n👤 **By:** @ShimulXDModZ", parse_mode="Markdown")
            os.remove(res_zip)
        else:
            bot.edit_message_text("❌ **Dumping Failed!** Check your files.", message.chat.id, status_msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"⚠️ **Error:** `{e}`", message.chat.id, status_msg.message_id)

    shutil.rmtree(work_dir, ignore_errors=True)
    if os.path.exists(out_dir): shutil.rmtree(out_dir)

bot.infinity_polling()
