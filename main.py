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

# --- MONGODB CONNECTION (SECURE & PERMANENT) ---
try:
    encoded_pass = urllib.parse.quote_plus("@%aN%#404%App@")
    MONGO_URI = f"mongodb+srv://apknebulix_modz:{encoded_pass}@apknebulix.suopcnt.mongodb.net/?appName=ApkNebulix"
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client['BlutterDB']
    users_col = db['users']
    banned_col = db['banned']
    client.admin.command('ping')
    print("✅ MongoDB Connected Successfully!")
except Exception as e:
    print(f"❌ MongoDB Error: {e}")

bot = telebot.TeleBot(TOKEN)

# --- DATABASE LOGIC ---
def register_user(user):
    if not users_col.find_one({"id": user.id}):
        users_col.insert_one({
            "id": user.id,
            "name": user.first_name,
            "username": user.username,
            "joined_at": time.strftime("%Y-%m-%d %H:%M:%S")
        })

def is_banned(user_id):
    return banned_col.find_one({"id": user_id}) is not None

# --- UI & ANIMATION HELPERS (ORIGINAL DESIGNS) ---
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

# --- 🛠️ 413 ERROR FIX: DOWNLOAD & UPLOAD LOGIC ---
def download_large_file(file_id, dest):
    """Bypasses 20MB download limit via stream"""
    file_info = bot.get_file(file_id)
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
    with requests.get(file_url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(dest, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                if chunk: f.write(chunk)
    return True

def upload_to_gofile(file_path):
    """Uploads large files (>50MB) to GoFile and returns the link"""
    try:
        server_resp = requests.get("https://api.gofile.io/getServer").json()
        if server_resp['status'] != 'ok': return None
        server = server_resp['data']['server']
        
        with open(file_path, 'rb') as f:
            res = requests.post(f"https://{server}.gofile.io/uploadFile", files={'file': f}).json()
        
        if res['status'] == 'ok':
            return res['data']['downloadPage']
    except: return None
    return None

# --- PREMIUM ADMIN PANEL (BUTTONS & COMMANDS) ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID: return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 Stats", callback_data="adm_stats"),
        types.InlineKeyboardButton("📜 User List", callback_data="adm_users"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="adm_bc"),
        types.InlineKeyboardButton("🚫 Ban/Unban", callback_data="adm_ban_manage"),
        types.InlineKeyboardButton("❌ Close Panel", callback_data="adm_close")
    )
    all_u = users_col.count_documents({})
    ban_u = banned_col.count_documents({})
    text = f"🛠 **ADMIN COMMAND CENTER**\n━━━━━━━━━━━━━━━━━━\n👥 **Total Users:** `{all_u}`\n🚫 **Banned:** `{ban_u}`"
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
def admin_actions(call):
    if call.from_user.id != ADMIN_ID: return
    if call.data == "adm_stats":
        all_u = users_col.count_documents({})
        bot.answer_callback_query(call.id, f"Registered Users: {all_u}", show_alert=True)
    elif call.data == "adm_users":
        users = users_col.find().limit(30)
        u_list = "📜 **Recent Users:**\n"
        for u in users: u_list += f"🔹 `{u['id']}` | {u['name']}\n"
        bot.send_message(call.message.chat.id, u_list, parse_mode="Markdown")
    elif call.data == "adm_bc":
        msg = bot.send_message(call.message.chat.id, "📩 Reply to this with the content to broadcast.")
        bot.register_for_reply(msg, broadcast_handler)
    elif call.data == "adm_ban_manage":
        bot.send_message(call.message.chat.id, "Use `/ban ID` or `/unban ID` to manage users.")
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
    bot.send_message(ADMIN_ID, f"📢 Broadcast Success: {s} | Fail: {f}")

@bot.message_handler(commands=['userinfo', 'ban', 'unban'])
def admin_cmds(message):
    if message.from_user.id != ADMIN_ID: return
    cmd = message.text.split()
    if len(cmd) < 2 and not message.reply_to_message: return
    
    uid = message.reply_to_message.from_user.id if message.reply_to_message else int(cmd[1])
    
    if "/ban" in message.text:
        banned_col.update_one({"id": uid}, {"$set": {"id": uid}}, upsert=True)
        bot.reply_to(message, f"✅ User `{uid}` Banned.")
    elif "/unban" in message.text:
        banned_col.delete_one({"id": uid})
        bot.reply_to(message, f"✅ User `{uid}` Unbanned.")
    elif "/userinfo" in message.text:
        user = users_col.find_one({"id": uid})
        if user:
            info = f"👤 **User Info**\nID: `{uid}`\nName: `{user['name']}`\nUsername: @{user.get('username','N/A')}"
            bot.reply_to(message, info, parse_mode="Markdown")

# --- START & WELCOME (UNCHANGED PREMIUM DESIGN) ---
@bot.message_handler(commands=['start'])
def welcome(message):
    register_user(message.from_user)
    if is_banned(message.from_user.id):
        return bot.reply_to(message, "🚫 **Access Denied!**")
    
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
        bot.edit_message_caption("✅ **Verified Successfully!**", call.message.chat.id, call.message.message_id)
    else: bot.answer_callback_query(call.id, "❌ Join channel first!", show_alert=True)

# --- CORE DUMPING (ORIGINAL LOGIC + 413 FIX) ---
@bot.message_handler(content_types=['document'])
def handle_dump(message):
    if is_banned(message.from_user.id) or not is_subscribed(message.from_user.id): return
    if not message.document.file_name.endswith('.zip'):
        return bot.reply_to(message, "❌ Send a `.zip` file.")

    uid = str(message.chat.id)
    work_dir, out_dir = f"work_{uid}", f"out_{uid}"
    shutil.rmtree(work_dir, ignore_errors=True)
    os.makedirs(work_dir)

    status_msg = bot.reply_to(message, "🛰 **Initializing Engine...**", parse_mode="Markdown")

    try:
        # Step 1: Download (Fixed 413)
        bot.send_chat_action(message.chat.id, 'typing')
        bot.edit_message_text(f"⏳ **Downloading File...**\n{create_progress_bar(40)}", 
                              message.chat.id, status_msg.message_id, parse_mode="Markdown")
        
        success = download_large_file(message.document.file_id, f"{work_dir}/input.zip")
        if not success: raise Exception("Download stream failed.")

        # Step 2: Extract
        bot.edit_message_text("📂 **Extracting Resources...**\n`Analyzing Bytecode...` ⚡", 
                              message.chat.id, status_msg.message_id, parse_mode="Markdown")
        with zipfile.ZipFile(f"{work_dir}/input.zip", 'r') as z: z.extractall(work_dir)

        # Step 3: Engine (Logic Intact)
        if not os.path.exists('blutter_src'):
            subprocess.run("git clone https://github.com/AbhiTheModder/blutter-termux.git blutter_src", shell=True)
        
        os.chdir('blutter_src')
        subprocess.run("find . -type f -exec sed -i 's/std::format/fmt::format/g' {} +", shell=True)
        
        start_t = time.time()
        process = subprocess.Popen(f"python3 blutter.py ../{work_dir} ../{out_dir}", shell=True)
        
        while process.poll() is None:
            bot.send_chat_action(message.chat.id, 'typing')
            elapsed = int(time.time() - start_t)
            bot.edit_message_text(f"{get_status_animation(elapsed)} **Dumping in Progress...**\n`Elapsed: {elapsed}s` ⏱\n`Status: Compiling C++` 🛠", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            time.sleep(4)
        os.chdir('..')

        # Step 4: Finalize & Multi-Method Upload
        if os.path.exists(out_dir) and any(os.scandir(out_dir)):
            res_zip = f"Blutter_Result_{uid}.zip"
            shutil.make_archive(res_zip.replace('.zip',''), 'zip', out_dir)
            
            f_size = os.path.getsize(res_zip) / (1024 * 1024)
            bot.edit_message_text(f"📦 **Dump Finished!**\nSize: `{f_size:.1f} MB`\n`Preparing delivery...` 📤", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            
            if f_size > 49.0:
                # 🛠️ 50MB+ BAG FIX: Upload to Cloud and send link
                bot.edit_message_text("☁️ **File too large for Telegram.**\n`Uploading to High-Speed Cloud...` 🚀", message.chat.id, status_msg.message_id, parse_mode="Markdown")
                link = upload_to_gofile(res_zip)
                if link:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("📥 Download Result", url=link))
                    bot.send_message(message.chat.id, f"✅ **Dump Success!**\n\nYour result is too large for Telegram, so I've uploaded it to a private link.\n\n⏱ Time: {int(time.time()-start_t)}s", reply_markup=markup, parse_mode="Markdown")
                else:
                    bot.edit_message_text("❌ Cloud upload failed. File too big.", message.chat.id, status_msg.message_id)
            else:
                # Normal Upload
                with open(res_zip, 'rb') as f:
                    bot.send_document(message.chat.id, f, caption=f"✅ **Dump Success!**\n⏱ Time: {int(time.time()-start_t)}s", parse_mode="Markdown")
            
            os.remove(res_zip)
        else:
            bot.edit_message_text("❌ **Dumping Failed!** Check files.", message.chat.id, status_msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"⚠️ **Engine Error:** `{e}`", message.chat.id, status_msg.message_id)

    shutil.rmtree(work_dir, ignore_errors=True)
    if os.path.exists(out_dir): shutil.rmtree(out_dir)

bot.infinity_polling()
