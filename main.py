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

bot = telebot.TeleBot(TOKEN)

# --- MONGODB CONNECTION (STABLE) ---
try:
    encoded_pass = urllib.parse.quote_plus("@%aN%#404%App@")
    MONGO_URI = f"mongodb+srv://apknebulix_modz:{encoded_pass}@apknebulix.suopcnt.mongodb.net/?appName=ApkNebulix"
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client['BlutterDB']
    users_col = db['users']
    banned_col = db['banned']
    client.admin.command('ping')
except Exception as e:
    print(f"MongoDB Notice: {e}")

# --- DATABASE LOGIC ---
def register_user(user):
    try:
        if not users_col.find_one({"id": user.id}):
            users_col.insert_one({"id": user.id, "name": user.first_name, "username": user.username})
    except: pass

def is_banned(user_id):
    try:
        return banned_col.find_one({"id": user_id}) is not None
    except: return False

# --- UI & ANIMATION HELPERS (ORIGINAL DESIGNS) ---
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

# --- 🛠️ SIMPLEST & 100% WORKING UPLOAD (CATBOX) ---
def upload_large_file(file_path):
    """Uploads files up to 200MB to Catbox.moe instantly"""
    try:
        url = "https://catbox.moe/user/api.php"
        data = {"reqtype": "fileupload"}
        with open(file_path, "rb") as f:
            files = {"fileToUpload": f}
            response = requests.post(url, data=data, files=files, timeout=300)
        if response.status_code == 200:
            return response.text # Returns direct link
    except: return None
    return None

# --- PREMIUM ADMIN PANEL ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID: return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 Stats", callback_data="adm_stats"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="adm_bc"),
        types.InlineKeyboardButton("🚫 Ban User", callback_data="adm_ban"),
        types.InlineKeyboardButton("❌ Close", callback_data="adm_close")
    )
    bot.send_message(message.chat.id, "🛠 **Admin Control Panel**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
def admin_callbacks(call):
    if call.from_user.id != ADMIN_ID: return
    if call.data == "adm_stats":
        u_count = users_col.count_documents({})
        bot.answer_callback_query(call.id, f"Registered Users: {u_count}", show_alert=True)
    elif call.data == "adm_close":
        bot.delete_message(call.message.chat.id, call.message.message_id)

# --- START & WELCOME (PREMIUM DESIGN UNCHANGED) ---
@bot.message_handler(commands=['start'])
def welcome(message):
    register_user(message.from_user)
    if is_banned(message.from_user.id):
        return bot.reply_to(message, "🚫 **Access Denied!**")
    
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

@bot.callback_query_handler(func=lambda call: call.data == "verify")
def verify_btn(call):
    if is_subscribed(call.from_user.id):
        bot.edit_message_caption("✅ **Verified Successfully!** Send your file.", call.message.chat.id, call.message.message_id)
    else: bot.answer_callback_query(call.id, "❌ Join channel first!", show_alert=True)

# --- CORE DUMPING ENGINE (ANIMATIONS & LOGIC) ---
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
        # Download
        bot.send_chat_action(message.chat.id, 'typing')
        for i in range(10, 101, 30):
            bot.edit_message_text(f"{get_status_animation(i)} **Downloading File...**\n{create_progress_bar(i)}", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            time.sleep(0.4)
        
        file_info = bot.get_file(message.document.file_id)
        download_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
        with requests.get(download_url, stream=True) as r:
            with open(f"{work_dir}/input.zip", 'wb') as f: shutil.copyfileobj(r.raw, f)

        # Extraction
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
        
        frame = 0
        while process.poll() is None:
            bot.send_chat_action(message.chat.id, 'typing')
            elapsed = int(time.time() - start_t)
            bot.edit_message_text(f"{get_status_animation(frame)} **Dumping in Progress...**\n`Elapsed: {elapsed}s` ⏱\n`Status: Compiling Core Assets` 🛠", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            frame += 1
            time.sleep(3)
        os.chdir('..')

        # FINAL UPLOAD LOGIC (FIXED ANTI-413)
        if os.path.exists(out_dir) and any(os.scandir(out_dir)):
            res_zip = f"Dump_{uid}.zip"
            shutil.make_archive(res_zip.replace('.zip',''), 'zip', out_dir)
            f_size = os.path.getsize(res_zip) / (1024 * 1024)

            if f_size > 49.0:
                # 🛠️ AUTOMATIC CATBOX UPLOAD FOR LARGE FILES
                bot.send_chat_action(message.chat.id, 'typing')
                bot.edit_message_text(f"☁️ **Size: {f_size:.1f}MB**\n`Uploading to High-Speed Cloud...` 🚀", 
                                      message.chat.id, status_msg.message_id, parse_mode="Markdown")
                
                link = upload_large_file(res_zip)
                if link:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("📥 Download Result", url=link))
                    bot.send_message(message.chat.id, f"✅ **Dump Success!**\n\nFile too large for Telegram, uploaded to cloud.\n⏱ Time: {int(time.time()-start_t)}s", 
                                     reply_markup=markup, parse_mode="Markdown")
                else:
                    bot.edit_message_text("❌ Cloud Upload Failed. File might be too large.", message.chat.id, status_msg.message_id)
            else:
                # NORMAL UPLOAD
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

print("🚀 Bot is running...")
bot.infinity_polling()
