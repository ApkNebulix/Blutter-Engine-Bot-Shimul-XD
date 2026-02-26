import os
import telebot
import subprocess
import shutil
import zipfile
import time
import requests
from telebot import types
from pymongo import MongoClient
import urllib.parse

# --- CONFIGURATION ---
TOKEN = '8635303381:AAH41sv7OVHm7WWAOFzKr3h68Fk0v0j2EvQ'
ADMIN_ID = 8381570120
IMAGE_URL = "https://raw.githubusercontent.com/ApkNebulix/Daroid-AN/refs/heads/main/Img/apknebulix.jpg"
REQUIRED_CHANNELS = ["@ShimulXDModZ"]

# --- MONGODB SETUP ---
# Password encoded for special characters (@%aN%#404%App@)
MONGO_URI = "mongodb+srv://apknebulix_modz:%40%25aN%25%23404%25App%40@apknebulix.suopcnt.mongodb.net/?appName=ApkNebulix"
client = MongoClient(MONGO_URI)
db = client['BlutterDB']
users_col = db['users']
banned_col = db['banned']

bot = telebot.TeleBot(TOKEN)

# --- DATABASE LOGIC ---
def register_user(user):
    if not users_col.find_one({"id": user.id}):
        users_col.insert_one({
            "id": user.id,
            "name": user.first_name,
            "username": user.username,
            "date": time.strftime("%Y-%m-%d %H:%M:%S")
        })

def is_banned(user_id):
    return banned_col.find_one({"id": user_id}) is not None

# --- UI HELPERS ---
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

# --- ERROR 413 FIX (Large File Downloader) ---
def download_large_file(file_id, dest_path):
    file_info = bot.get_file(file_id)
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
    response = requests.get(file_url, stream=True)
    if response.status_code == 200:
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    return False

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID: return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 Stats", callback_data="stats"),
        types.InlineKeyboardButton("📜 User List", callback_data="user_list"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="bc_info"),
        types.InlineKeyboardButton("❌ Close", callback_data="close_admin")
    )
    all_users = users_col.count_documents({})
    banned_users = banned_col.count_documents({})
    admin_text = (
        "🛠 **Admin Command Center**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👥 **Total Users:** `{all_users}`\n"
        f"🚫 **Banned:** `{banned_users}`"
    )
    bot.send_message(message.chat.id, admin_text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(commands=['userinfo'])
def get_user_info(message):
    if message.from_user.id != ADMIN_ID: return
    # If replied to a message, get that user's info, else show all
    users = users_col.find().limit(50)
    user_list_text = "📜 **User List (Last 50):**\n━━━━━━━━━━━━━━━━━━\n"
    for u in users:
        user_list_text += f"🔹 `{u['id']}` | {u['name']}\n"
    bot.reply_to(message, user_list_text, parse_mode="Markdown")

@bot.message_handler(commands=['ban'])
def ban_user(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        target_id = None
        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
        else:
            target_id = int(message.text.split()[1])
        
        if not banned_col.find_one({"id": target_id}):
            banned_col.insert_one({"id": target_id})
            bot.reply_to(message, f"✅ User `{target_id}` banned successfully.")
    except: bot.reply_to(message, "❌ Use: `/ban ID` or reply to a user.")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        target_id = int(message.text.split()[1])
        banned_col.delete_one({"id": target_id})
        bot.reply_to(message, f"✅ User `{target_id}` unbanned.")
    except: bot.reply_to(message, "❌ Use: `/unban ID`")

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.from_user.id != ADMIN_ID: return
    if not message.reply_to_message:
        return bot.reply_to(message, "❌ Reply to a message to broadcast.")
    
    users = users_col.find()
    success, fail = 0, 0
    msg_id = bot.send_message(message.chat.id, "🚀 **Broadcasting...**").message_id
    
    for user in users:
        try:
            bot.copy_message(user['id'], message.chat.id, message.reply_to_message.message_id)
            success += 1
            time.sleep(0.05)
        except: fail += 1
    
    bot.edit_message_text(f"📢 **Broadcast Finished!**\n✅ Success: {success}\n❌ Fail: {fail}", message.chat.id, msg_id)

# --- CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if call.data == "verify":
        if is_subscribed(call.from_user.id):
            bot.edit_message_caption("✅ **Verified!** You can now send files.", call.message.chat.id, call.message.message_id)
        else: bot.answer_callback_query(call.id, "❌ Join the channel first!", show_alert=True)
    elif call.data == "stats":
        all_u = users_col.count_documents({})
        ban_u = banned_col.count_documents({})
        bot.answer_callback_query(call.id, f"Users: {all_u} | Banned: {ban_u}", show_alert=True)
    elif call.data == "user_list":
        get_user_info(call.message)
    elif call.data == "close_admin":
        bot.delete_message(call.message.chat.id, call.message.message_id)

# --- CORE LOGIC ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    register_user(message.from_user.id, message.from_user.first_name) if 'register_user' in globals() else None
    # Fix for register_user call
    if not users_col.find_one({"id": message.from_user.id}):
        users_col.insert_one({"id": message.from_user.id, "name": message.from_user.first_name})

    if is_banned(message.from_user.id):
        return bot.reply_to(message, "🚫 You are banned.")

    if not is_subscribed(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        for ch in REQUIRED_CHANNELS:
            markup.add(types.InlineKeyboardButton(text="Join Channel 📢", url=f"https://t.me/{ch[1:]}"))
        markup.add(types.InlineKeyboardButton(text="🔄 Verify Membership", callback_data="verify"))
        return bot.send_photo(message.chat.id, IMAGE_URL, caption="⚠️ **Join our channel to use this bot.**", reply_markup=markup)

    welcome_text = (
        "╔════════════════════╗\n"
        "     🚀 **BLUTTER PRO ENGINE**\n"
        "╚════════════════════╝\n"
        "🔹 **Status:** `Online` ✅\n"
        "🔹 **Dev:** @ShimulXD\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📥 Send a `.zip` file with `libflutter.so` and `libapp.so`."
    )
    bot.send_photo(message.chat.id, IMAGE_URL, caption=welcome_text, parse_mode="Markdown")

@bot.message_handler(content_types=['document'])
def dump_handler(message):
    if is_banned(message.from_user.id) or not is_subscribed(message.from_user.id): return

    if not message.document.file_name.endswith('.zip'):
        return bot.reply_to(message, "❌ Send a .zip file.")

    uid = str(message.chat.id)
    work_dir, out_dir = f"work_{uid}", f"out_{uid}"
    shutil.rmtree(work_dir, ignore_errors=True)
    os.makedirs(work_dir)

    status = bot.reply_to(message, "🛰 **Initializing...**", parse_mode="Markdown")

    try:
        # Step 1: Download (Handle 413 error by using direct requests stream)
        bot.edit_message_text("📥 **Downloading Large File...**", message.chat.id, status.message_id)
        bot.send_chat_action(message.chat.id, 'typing')
        
        success = download_large_file(message.document.file_id, f"{work_dir}/input.zip")
        if not success: raise Exception("Download failed.")

        # Step 2: Extract
        bot.edit_message_text("📂 **Extracting...**", message.chat.id, status.message_id)
        with zipfile.ZipFile(f"{work_dir}/input.zip", 'r') as z: z.extractall(work_dir)

        # Step 3: Engine Run
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

        # Step 4: Finalize & Upload
        if os.path.exists(out_dir) and any(os.scandir(out_dir)):
            res_zip = f"Dump_{uid}.zip"
            shutil.make_archive(res_zip.replace('.zip',''), 'zip', out_dir)
            
            # 413 Error Fix during Upload (Telegram limit is 50MB for bots)
            if os.path.getsize(res_zip) > 50 * 1024 * 1024:
                bot.edit_message_text("⚠️ **Result too large (>50MB).** Splitting/Linking not supported on basic Bot API.", message.chat.id, status.message_id)
            else:
                with open(res_zip, 'rb') as f:
                    bot.send_document(message.chat.id, f, caption=f"✅ **Success!**\nTime: {int(time.time()-start_t)}s")
            os.remove(res_zip)
        else:
            bot.edit_message_text("❌ **Dump Failed.** Check libs.", message.chat.id, status.message_id)

    except Exception as e:
        bot.edit_message_text(f"⚠️ **Error:** `{str(e)}`", message.chat.id, status.message_id)

    shutil.rmtree(work_dir, ignore_errors=True)
    shutil.rmtree(out_dir, ignore_errors=True)

bot.infinity_polling()
