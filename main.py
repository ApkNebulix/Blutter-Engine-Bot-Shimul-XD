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

# --- 100% CORRECT CONFIGURATION ---
TOKEN = '8635303381:AAH41sv7OVHm7WWAOFzKr3h68Fk0v0j2EvQ' 
ADMIN_ID = 8381570120
IMAGE_URL = "https://raw.githubusercontent.com/ApkNebulix/Daroid-AN/refs/heads/main/Img/apknebulix.jpg"
REQUIRED_CHANNELS = ["@ShimulXDModZ"]
GOFILE_TOKEN = 'q0RU1AwomWPBtWyIu4VVCS9vuo6kAJLI'

# Initialize Bot
bot = telebot.TeleBot(TOKEN)

# --- MONGODB CONNECTION (STABILIZED) ---
try:
    encoded_pass = urllib.parse.quote_plus("@%aN%#404%App@")
    MONGO_URI = f"mongodb+srv://apknebulix_modz:{encoded_pass}@apknebulix.suopcnt.mongodb.net/?appName=ApkNebulix"
    # Added timeout to prevent hanging
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client['BlutterDB']
    users_col = db['users']
    banned_col = db['banned']
    client.admin.command('ping')
    print("✅ MongoDB Connected Successfully!")
except Exception as e:
    print(f"⚠️ MongoDB Warning: {e} (Bot will still try to run)")

# --- DATABASE FUNCTIONS ---
def register_user(user):
    try:
        if not users_col.find_one({"id": user.id}):
            users_col.insert_one({"id": user.id, "name": user.first_name, "username": user.username})
    except: pass

def is_banned(user_id):
    try:
        return banned_col.find_one({"id": user_id}) is not None
    except: return False

# --- UI & ANIMATION HELPERS ---
def create_progress_bar(percent):
    done = int(percent / 10)
    bar = "🟢" * done + "⚪" * (10 - done)
    return f"{bar} {percent}%"

def get_status_animation(frame):
    frames = ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘", "🪐", "🛰", "💎"]
    return frames[frame % len(frames)]

def is_subscribed(user_id):
    if user_id == ADMIN_ID: return True
    try:
        for channel in REQUIRED_CHANNELS:
            status = bot.get_chat_member(channel, user_id).status
            if status in ['left', 'kicked']: return False
        return True
    except: return True

# --- GOFILE UPLOAD LOGIC ---
def upload_to_gofile(file_path):
    try:
        server_req = requests.get("https://api.gofile.io/getServer", timeout=10).json()
        server = server_req['data']['server']
        with open(file_path, 'rb') as f:
            res = requests.post(
                f"https://{server}.gofile.io/uploadFile",
                files={'file': f},
                data={'token': GOFILE_TOKEN},
                timeout=300
            ).json()
        if res['status'] == 'ok':
            return res['data']['downloadPage']
    except: return None

# --- WELCOME SCREEN WITH PREMIUM BUTTONS ---
@bot.message_handler(commands=['start'])
def welcome(message):
    register_user(message.from_user)
    if is_banned(message.from_user.id):
        return bot.reply_to(message, "🚫 **Access Denied!** You are banned.")
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📢 Channel", url="https://t.me/ShimulXDModZ"),
        types.InlineKeyboardButton("👤 Developer", url="https://t.me/ShimulXD"),
        types.InlineKeyboardButton("🔄 Verify Join", callback_data="verify"),
        types.InlineKeyboardButton("🛠 Support", url="https://t.me/ShimulXDModZ")
    )

    if not is_subscribed(message.from_user.id):
        bot.send_photo(message.chat.id, IMAGE_URL, 
                       caption=f"👋 **Hello {message.from_user.first_name}!**\n\n⚠️ **Membership Required:**\nYou must join our official channel to use the Blutter Pro Engine.",
                       reply_markup=markup, parse_mode="Markdown")
        return

    welcome_text = (
        "╔════════════════════╗\n"
        "     🚀 **BLUTTER ENGINE PRO**\n"
        "╚════════════════════╝\n"
        "🔹 **Status:** `Online / Ready` ✅\n"
        "🔹 **Dev:** @ShimulXD\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📥 **Send a .zip file containing:**\n"
        "📂 `libflutter.so` & `libapp.so` \n"
        "━━━━━━━━━━━━━━━━━━\n"
        "✨ **All Features Enabled & 100% Fixed!**"
    )
    bot.send_photo(message.chat.id, IMAGE_URL, caption=welcome_text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    if call.data == "verify":
        if is_subscribed(call.from_user.id):
            bot.edit_message_caption("✅ **Verified Successfully!** You can now send files.", call.message.chat.id, call.message.message_id)
        else: bot.answer_callback_query(call.id, "❌ Join channel first!", show_alert=True)

# --- ADMIN PANEL ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID: return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📊 Stats", callback_data="stats"))
    bot.send_message(message.chat.id, "🛠 **Admin Control Panel**", reply_markup=markup)

# --- CORE DUMPING ENGINE ---
@bot.message_handler(content_types=['document'])
def handle_docs(message):
    if is_banned(message.from_user.id) or not is_subscribed(message.from_user.id): return
    if not message.document.file_name.endswith('.zip'):
        return bot.reply_to(message, "❌ **Error:** Please send a `.zip` file.")

    uid = str(message.chat.id)
    work_dir, out_dir = f"work_{uid}", f"out_{uid}"
    shutil.rmtree(work_dir, ignore_errors=True)
    os.makedirs(work_dir)

    status_msg = bot.reply_to(message, "🛰 **Initializing Pro Engine...**", parse_mode="Markdown")

    try:
        # Step 1: Download with Animation
        bot.send_chat_action(message.chat.id, 'typing')
        for i in range(10, 101, 30):
            bot.edit_message_text(f"{get_status_animation(i)} **Downloading File...**\n{create_progress_bar(i)}", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            time.sleep(0.4)
        
        file_info = bot.get_file(message.document.file_id)
        download_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
        with requests.get(download_url, stream=True) as r:
            with open(f"{work_dir}/input.zip", 'wb') as f: shutil.copyfileobj(r.raw, f)

        # Step 2: Extraction
        bot.edit_message_text("📂 **Extracting Resources...**\n`Analyzing Flutter Bytecode...` ⚡", message.chat.id, status_msg.message_id, parse_mode="Markdown")
        with zipfile.ZipFile(f"{work_dir}/input.zip", 'r') as z: z.extractall(work_dir)

        # Step 3: Engine Run
        if not os.path.exists('blutter_src'):
            subprocess.run("git clone https://github.com/AbhiTheModder/blutter-termux.git blutter_src", shell=True)
        
        os.chdir('blutter_src')
        subprocess.run("find . -type f -exec sed -i 's/std::format/fmt::format/g' {} +", shell=True)
        
        start_t = time.time()
        process = subprocess.Popen(f"python3 blutter.py ../{work_dir} ../{out_dir}", shell=True)
        
        # Advanced Animation Loop
        frame = 0
        while process.poll() is None:
            bot.send_chat_action(message.chat.id, 'typing')
            elapsed = int(time.time() - start_t)
            bot.edit_message_text(f"{get_status_animation(frame)} **Dumping in Progress...**\n`Elapsed: {elapsed}s` ⏱\n`Status: Compiling Core Assets` 🛠", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            frame += 1
            time.sleep(3)
        os.chdir('..')

        # Step 4: Finalize & Upload (ANTI-413)
        if os.path.exists(out_dir) and any(os.scandir(out_dir)):
            res_zip = f"Blutter_Output_{uid}.zip"
            shutil.make_archive(res_zip.replace('.zip',''), 'zip', out_dir)
            f_size = os.path.getsize(res_zip) / (1024 * 1024)

            if f_size > 49.0:
                bot.edit_message_text(f"☁️ **Size: {f_size:.1f}MB**\n`Uploading to Cloud Server...` 🚀", message.chat.id, status_msg.message_id, parse_mode="Markdown")
                download_link = upload_to_gofile(res_zip)
                if download_link:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("📥 Download Result", url=download_link))
                    bot.send_message(message.chat.id, f"✅ **Dump Successful!**\nTime: {int(time.time()-start_t)}s", reply_markup=markup, parse_mode="Markdown")
                else:
                    bot.edit_message_text("❌ Cloud Upload Failed.", message.chat.id, status_msg.message_id)
            else:
                bot.send_chat_action(message.chat.id, 'upload_document')
                with open(res_zip, 'rb') as f:
                    bot.send_document(message.chat.id, f, caption=f"✅ **Dump Success!**\n⏱ Time: {int(time.time()-start_t)}s")
            os.remove(res_zip)
        else:
            bot.edit_message_text("❌ **Dumping Failed!** Check libs.", message.chat.id, status_msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"⚠️ **Engine Error:** `{e}`", message.chat.id, status_msg.message_id)

    shutil.rmtree(work_dir, ignore_errors=True)
    if os.path.exists(out_dir): shutil.rmtree(out_dir)

# --- ROBUST POLLING ---
print("🚀 Blutter Bot is starting...")
bot.infinity_polling(timeout=60, long_polling_timeout=60)
