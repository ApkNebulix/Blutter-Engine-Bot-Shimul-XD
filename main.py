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
from datetime import datetime, timedelta

# --- 100% CORRECT CONFIGURATION ---
TOKEN = '8635303381:AAH41sv7OVHm7WWAOFzKr3h68Fk0v0j2EvQ' 
ADMIN_ID = 8381570120
IMAGE_URL = "https://raw.githubusercontent.com/ApkNebulix/Daroid-AN/refs/heads/main/Img/apknebulix.jpg"
REQUIRED_CHANNELS = ["@ShimulXDModZ"]

bot = telebot.TeleBot(TOKEN)

# --- GLOBAL STATE & CONCURRENCY ---
current_dumps = 0 # Track active dumping processes
active_users = {} # Track live users (last 5 mins)

# --- MONGODB CONNECTION ---
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

# --- DATABASE & TRACKING LOGIC ---
def register_user(user):
    active_users[user.id] = datetime.now() # Update live status
    try:
        if not users_col.find_one({"id": user.id}):
            users_col.insert_one({"id": user.id, "name": user.first_name, "username": user.username})
    except: pass

def is_banned(user_id):
    try: return banned_col.find_one({"id": user_id}) is not None
    except: return False

def get_live_count():
    now = datetime.now()
    return len([uid for uid, ltime in active_users.items() if now - ltime < timedelta(minutes=5)])

# --- UI HELPERS ---
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

def upload_large_file(file_path):
    try:
        url = "https://catbox.moe/user/api.php"
        data = {"reqtype": "fileupload"}
        with open(file_path, "rb") as f:
            files = {"fileToUpload": f}
            response = requests.post(url, data=data, files=files, timeout=300)
        return response.text if response.status_code == 200 else None
    except: return None

# --- ADVANCED ADMIN PANEL ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID: return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🌍 Global State", callback_data="adm_state"),
        types.InlineKeyboardButton("📜 User List", callback_data="adm_users"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="adm_bc"),
        types.InlineKeyboardButton("🚫 Ban/Unban", callback_data="adm_ban_panel"),
        types.InlineKeyboardButton("❌ Close", callback_data="adm_close")
    )
    bot.send_message(message.chat.id, "🛠 **Admin Control Panel**\nWelcome back, Shimul XD!", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
def admin_callbacks(call):
    if call.from_user.id != ADMIN_ID: return
    
    if call.data == "adm_state":
        total = users_col.count_documents({})
        live = get_live_count()
        bot.send_message(call.message.chat.id, f"🌍 **Global Statistics**\n\n🔹 Total Users: `{total}`\n🔹 Real-time Live: `{live}`\n🔹 Active Dumps: `{current_dumps}/5`", parse_mode="Markdown")
    
    elif call.data == "adm_users":
        users = users_col.find().limit(50)
        text = "📜 **User List (ID & Name):**\n"
        for u in users: text += f"🔹 `{u['id']}` | {u['name']}\n"
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

    elif call.data == "adm_bc":
        msg = bot.send_message(call.message.chat.id, "📩 **Reply to this message** with the content (Text/Photo/Video) you want to broadcast.")
        bot.register_for_reply(msg, broadcast_handler)

    elif call.data == "adm_ban_panel":
        bot.send_message(call.message.chat.id, "Use: `/ban ID` to ban or `/unban ID` to unban.")

    elif call.data == "adm_close":
        bot.delete_message(call.message.chat.id, call.message.message_id)

def broadcast_handler(message):
    users = users_col.find()
    s, f = 0, 0
    for u in users:
        try:
            bot.copy_message(u['id'], message.chat.id, message.message_id)
            s += 1
            time.sleep(0.05)
        except: f += 1
    bot.send_message(ADMIN_ID, f"📢 **Broadcast Complete!**\n✅ Success: {s} | ❌ Fail: {f}")

@bot.message_handler(commands=['ban', 'unban'])
def ban_unban_cmd(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        uid = int(message.text.split()[1])
        if "unban" in message.text:
            banned_col.delete_one({"id": uid})
            bot.reply_to(message, f"✅ User `{uid}` unbanned.")
        else:
            banned_col.update_one({"id": uid}, {"$set": {"id": uid}}, upsert=True)
            bot.reply_to(message, f"🚫 User `{uid}` banned.")
    except: bot.reply_to(message, "❌ Use: `/ban ID` or `/unban ID`.")

# --- WELCOME SCREEN (3 BUTTONS & CONCURRENCY STATUS) ---
@bot.message_handler(commands=['start'])
def welcome(message):
    register_user(message.from_user)
    if is_banned(message.from_user.id):
        return bot.reply_to(message, "🚫 **Access Denied!**")
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📢 Official Channel", url="https://t.me/ShimulXDModZ"),
        types.InlineKeyboardButton("👤 Developer Info", url="https://t.me/ShimulXD"),
        types.InlineKeyboardButton("🛠 Technical Support", url="https://t.me/ShimulXDModZ")
    )

    live_dumps = f"🟢 Server Load: `{current_dumps}/5`" if current_dumps < 5 else f"🔴 Server Load: `{current_dumps}/5 (Busy)`"
    
    welcome_text = (
        "╔════════════════════╗\n"
        "     🚀 **BLUTTER ENGINE PRO**\n"
        "╚════════════════════╝\n"
        "🔹 **Status:** `Online` ✅\n"
        f"🔹 {live_dumps}\n"
        "🔹 **Dev:** @ShimulXD\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📥 **Send a .zip file containing:**\n"
        "📂 `libflutter.so` & `libapp.so` \n"
        "━━━━━━━━━━━━━━━━━━\n"
        "✨ **Maximum Efficiency & High-Speed.**"
    )
    bot.send_photo(message.chat.id, IMAGE_URL, caption=welcome_text, reply_markup=markup, parse_mode="Markdown")

# --- CORE DUMPING (CONCURRENCY & ANIMATIONS) ---
@bot.message_handler(content_types=['document'])
def handle_docs(message):
    global current_dumps
    user_id = message.from_user.id
    register_user(message.from_user)
    
    if is_banned(user_id): return
    if not is_subscribed(user_id):
        return bot.reply_to(message, "⚠️ **Join @ShimulXDModZ first to use the engine!**")

    # Concurrency Check
    if current_dumps >= 5 and user_id != ADMIN_ID:
        return bot.reply_to(message, "⚠️ **Server Busy!**\nMaximum 5 users are dumping right now. Please wait 1-2 minutes and try again.")

    if not message.document.file_name.endswith('.zip'):
        return bot.reply_to(message, "❌ **Error:** Please send a `.zip` file.")

    current_dumps += 1 # Increment session
    uid = str(message.chat.id)
    work_dir, out_dir = f"work_{uid}", f"out_{uid}"
    shutil.rmtree(work_dir, ignore_errors=True)
    os.makedirs(work_dir)

    status_msg = bot.reply_to(message, "🛡 **Verifying Membership...**", parse_mode="Markdown")
    time.sleep(1)
    
    # Verification Animation
    for i in range(3):
        bot.edit_message_text(f"💎 **Authenticating...** {'.' * (i+1)}", message.chat.id, status_msg.message_id)
        time.sleep(0.5)

    try:
        # Download
        bot.send_chat_action(message.chat.id, 'typing')
        bot.edit_message_text("🛰 **Downloading File...**", message.chat.id, status_msg.message_id)
        
        file_info = bot.get_file(message.document.file_id)
        download_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
        with requests.get(download_url, stream=True) as r:
            with open(f"{work_dir}/input.zip", 'wb') as f: shutil.copyfileobj(r.raw, f)

        # Extraction
        bot.edit_message_text("📂 **Extracting Resources...**", message.chat.id, status_msg.message_id)
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
            ani = get_status_animation(frame)
            bot.edit_message_text(f"{ani} **Dumping in Progress...**\n`Elapsed: {elapsed}s` ⏱\n`Status: Compiling Core Assets` 🛠", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            frame += 1
            time.sleep(3)
        os.chdir('..')

        # Final Upload (Catbox for Large Files)
        if os.path.exists(out_dir) and any(os.scandir(out_dir)):
            res_zip = f"Dump_{uid}.zip"
            shutil.make_archive(res_zip.replace('.zip',''), 'zip', out_dir)
            f_size = os.path.getsize(res_zip) / (1024 * 1024)

            if f_size > 49.0:
                bot.edit_message_text(f"☁️ **Size: {f_size:.1f}MB**\n`Uploading to Cloud...` 🚀", message.chat.id, status_msg.message_id)
                link = upload_large_file(res_zip)
                if link:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("📥 Download Result", url=link))
                    bot.send_message(message.chat.id, f"✅ **Dump Success!**\nTime: {int(time.time()-start_t)}s", reply_markup=markup, parse_mode="Markdown")
                else: bot.edit_message_text("❌ Cloud Upload Failed.", message.chat.id, status_msg.message_id)
            else:
                bot.send_chat_action(message.chat.id, 'upload_document')
                with open(res_zip, 'rb') as f:
                    bot.send_document(message.chat.id, f, caption=f"✅ **Dump Success!**\n⏱ Time: {int(time.time()-start_t)}s")
            
            os.remove(res_zip)
        else: bot.edit_message_text("❌ **Dumping Failed!**", message.chat.id, status_msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"⚠️ **Error:** `{e}`", message.chat.id, status_msg.message_id)

    finally:
        current_dumps -= 1 # Crucial: Always decrement
        shutil.rmtree(work_dir, ignore_errors=True)
        if os.path.exists(out_dir): shutil.rmtree(out_dir)

print("🚀 Bot is running...")
bot.infinity_polling()
