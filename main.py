import os
import telebot
import subprocess
import shutil
import zipfile
import time
import requests
from telebot import types
from pymongo import MongoClient

# --- CONFIGURATION ---
TOKEN = '8635303381:AAH41sv7OVHm7WWAOFzKr3h68Fk0v0j2EvQ'
ADMIN_ID = 8381570120
IMAGE_URL = "https://raw.githubusercontent.com/ApkNebulix/Daroid-AN/refs/heads/main/Img/apknebulix.jpg"
REQUIRED_CHANNELS = ["@ShimulXDModZ"]

# MongoDB Connection
MONGO_URI = "mongodb+srv://apknebulix_modz:@%aN%#404%App@@apknebulix.suopcnt.mongodb.net/?appName=ApkNebulix"
client = MongoClient(MONGO_URI)
db = client['bot_database']
users_col = db['users']
banned_col = db['banned_users']

bot = telebot.TeleBot(TOKEN)

# --- DATABASE HELPERS ---
def register_user(user):
    if not users_col.find_one({"user_id": user.id}):
        users_col.insert_one({
            "user_id": user.id,
            "first_name": user.first_name,
            "username": user.username
        })

def is_banned(user_id):
    return banned_col.find_one({"user_id": user_id}) is not None

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
    except:
        return True

# --- LARGE FILE DOWNLOADER (Fix 413 Error) ---
def download_large_file(file_id, save_path):
    file_info = bot.get_file(file_id)
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
    response = requests.get(file_url, stream=True)
    if response.status_code == 200:
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    return False

# --- MIDDLEWARE & SECURITY ---
@bot.message_handler(func=lambda m: is_banned(m.from_user.id))
def handle_banned(message):
    bot.reply_to(message, "🚫 **Access Denied!**\nYou are banned from using this bot.")

# --- ADMIN PANEL COMMANDS ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID: return
    total_users = users_col.count_documents({})
    total_banned = banned_col.count_documents({})
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 Stats", callback_data="stats"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="broadcast_info"),
        types.InlineKeyboardButton("📜 User List", callback_data="user_list"),
        types.InlineKeyboardButton("❌ Close", callback_data="close_admin")
    )
    
    admin_text = (
        "🛠 **Admin Command Center**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👤 **Admin:** `Shimul XD`\n"
        f"👥 **Total Users:** `{total_users}`\n"
        f"🚫 **Banned:** `{total_banned}`"
    )
    bot.send_message(message.chat.id, admin_text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(commands=['userinfo'])
def get_all_users_info(message):
    if message.from_user.id != ADMIN_ID: return
    all_users = users_col.find()
    info_text = "📜 **Bot User List (ID + Name):**\n━━━━━━━━━━━━━━━━━━\n"
    for user in all_users:
        info_text += f"🔹 `{user['user_id']}` | {user['first_name']}\n"
    
    if len(info_text) > 4000: # টেলিগ্রাম টেক্সট লিমিট হ্যান্ডেল করা
        with open("users.txt", "w") as f: f.write(info_text)
        bot.send_document(message.chat.id, open("users.txt", "rb"))
    else:
        bot.send_message(message.chat.id, info_text, parse_mode="Markdown")

@bot.message_handler(commands=['ban'])
def ban_user(message):
    if message.from_user.id != ADMIN_ID: return
    target_id = None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    elif len(message.text.split()) > 1:
        target_id = int(message.text.split()[1])

    if target_id:
        if not banned_col.find_one({"user_id": target_id}):
            banned_col.insert_one({"user_id": target_id})
            bot.reply_to(message, f"✅ User `{target_id}` has been banned.")
    else:
        bot.reply_to(message, "❌ Reply to a message or provide User ID.")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    if message.from_user.id != ADMIN_ID: return
    target_id = None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    elif len(message.text.split()) > 1:
        target_id = int(message.text.split()[1])

    if target_id:
        banned_col.delete_one({"user_id": target_id})
        bot.reply_to(message, f"✅ User `{target_id}` has been unbanned.")

@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    if message.from_user.id != ADMIN_ID: return
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Reply to a message to broadcast.")
        return
    
    users = users_col.find()
    success, fail = 0, 0
    bot.send_message(message.chat.id, "🚀 **Broadcasting...**")
    for user in users:
        try:
            bot.copy_message(user['user_id'], message.chat.id, message.reply_to_message.message_id)
            success += 1
            time.sleep(0.05)
        except:
            fail += 1
    bot.send_message(message.chat.id, f"✅ Done! Success: {success}, Failed: {fail}")

# --- CALLBACK HANDLERS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    if call.data == "verify":
        if is_subscribed(call.from_user.id):
            bot.edit_message_caption("✅ **Verified!** Send your zip file.", call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "❌ Join the channel!", show_alert=True)
    elif call.data == "user_list":
        get_all_users_info(call.message)
    elif call.data == "close_admin":
        bot.delete_message(call.message.chat.id, call.message.message_id)

# --- START ---
@bot.message_handler(commands=['start'])
def welcome(message):
    register_user(message.from_user)
    if not is_subscribed(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        for ch in REQUIRED_CHANNELS:
            markup.add(types.InlineKeyboardButton(text="Join Channel 📢", url=f"https://t.me/{ch[1:]}"))
        markup.add(types.InlineKeyboardButton(text="🔄 Verify Membership", callback_data="verify"))
        bot.send_photo(message.chat.id, IMAGE_URL, caption=f"👋 **Hello!**\nJoin our channel to use **Blutter Pro Engine**.", reply_markup=markup)
        return

    welcome_text = (
        "╔════════════════════╗\n"
        "     🚀 **BLUTTER ENGINE PRO**\n"
        "╚════════════════════╝\n"
        "🔹 **Status:** `Online` ✅\n"
        "🔹 **Dev:** @ShimulXD\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📥 Send a `.zip` file containing `libflutter.so` & `libapp.so`."
    )
    bot.send_photo(message.chat.id, IMAGE_URL, caption=welcome_text, parse_mode="Markdown")

# --- DUMPING PROCESS ---
@bot.message_handler(content_types=['document'])
def start_dump_process(message):
    if not is_subscribed(message.from_user.id) or is_banned(message.from_user.id): return
    if not message.document.file_name.endswith('.zip'):
        bot.reply_to(message, "❌ Send a `.zip` file.")
        return

    uid = str(message.chat.id)
    work_dir, out_dir = f"work_{uid}", f"out_{uid}"
    if os.path.exists(work_dir): shutil.rmtree(work_dir)
    os.makedirs(work_dir)

    status_msg = bot.reply_to(message, "🛰 **Initializing Engine...**", parse_mode="Markdown")

    try:
        # Step 1: Large File Download Fix
        bot.edit_message_text(f"📥 **Downloading Large File...**\n{create_progress_bar(30)}", message.chat.id, status_msg.message_id, parse_mode="Markdown")
        success = download_large_file(message.document.file_id, f"{work_dir}/input.zip")
        
        if not success:
            bot.edit_message_text("❌ Download failed.", message.chat.id, status_msg.message_id)
            return

        # Step 2: Extract
        with zipfile.ZipFile(f"{work_dir}/input.zip", 'r') as z: z.extractall(work_dir)

        # Step 3: Dumping Logic
        if not os.path.exists('blutter_src'):
            subprocess.run("git clone https://github.com/AbhiTheModder/blutter-termux.git blutter_src", shell=True)
        
        os.chdir('blutter_src')
        subprocess.run("find . -type f -exec sed -i 's/std::format/fmt::format/g' {} +", shell=True)
        
        start_t = time.time()
        process = subprocess.Popen(f"python3 blutter.py ../{work_dir} ../{out_dir}", shell=True)
        
        while process.poll() is None:
            elapsed = int(time.time() - start_t)
            bot.edit_message_text(f"⚡ **Dumping in Progress...**\n`Time: {elapsed}s`\n`Status: Compiling Core`", message.chat.id, status_msg.message_id, parse_mode="Markdown")
            time.sleep(5)

        os.chdir('..')

        # Step 4: Finalizing
        if os.path.exists(out_dir) and any(os.scandir(out_dir)):
            res_zip = f"Blutter_Output_{uid}.zip"
            shutil.make_archive(res_zip.replace('.zip',''), 'zip', out_dir)
            with open(res_zip, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"✅ **Dump Success!**\n👤 **By:** @ShimulXDModZ", parse_mode="Markdown")
            os.remove(res_zip)
        else:
            bot.edit_message_text("❌ Dumping failed. Check files.", message.chat.id, status_msg.message_id)

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ **System Error:** `{str(e)}`")

    shutil.rmtree(work_dir, ignore_errors=True)
    if os.path.exists(out_dir): shutil.rmtree(out_dir)

bot.infinity_polling()
