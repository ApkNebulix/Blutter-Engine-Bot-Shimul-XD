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

# --- 100% SUPREME CONFIGURATION ---
TOKEN = '8635303381:AAH41sv7OVHm7WWAOFzKr3h68Fk0v0j2EvQ' 
ADMIN_ID = 8381570120
LOG_CHANNEL = "@BotControlPanel" 
IMAGE_URL = "https://raw.githubusercontent.com/ApkNebulix/Daroid-AN/refs/heads/main/Img/apknebulix.jpg"
REQUIRED_CHANNELS = ["@ShimulXDModZ"]

bot = telebot.TeleBot(TOKEN)

# --- GLOBAL TRACKING ---
active_dumps = 0
CONCURRENCY_LIMIT = 5

# --- MONGODB CONNECTION ---
try:
    encoded_pass = urllib.parse.quote_plus("@%aN%#404%App@")
    MONGO_URI = f"mongodb+srv://apknebulix_modz:{encoded_pass}@apknebulix.suopcnt.mongodb.net/?appName=ApkNebulix"
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client['BlutterUltra']
    users_col = db['users']
    banned_col = db['banned']
    client.admin.command('ping')
except Exception as e:
    print(f"❌ DB Notice: {e}")

# --- HELPER FUNCTIONS ---
def send_log(text):
    try: bot.send_message(LOG_CHANNEL, f"🛡 **[SYSTEM LOG]**\n{text}", parse_mode="Markdown")
    except: pass

def register_user(user):
    try:
        users_col.update_one(
            {"id": user.id},
            {"$set": {"id": user.id, "name": user.first_name, "username": user.username, "last_active": datetime.now()}},
            upsert=True
        )
    except: pass

def is_subscribed(user_id):
    if user_id == ADMIN_ID: return True
    try:
        for ch in REQUIRED_CHANNELS:
            status = bot.get_chat_member(ch, user_id).status
            if status in ['left', 'kicked']: return False
        return True
    except: return True

def is_banned(user_id):
    return banned_col.find_one({"id": user_id}) is not None

def upload_to_catbox(file_path):
    try:
        url = "https://catbox.moe/user/api.php"
        data = {"reqtype": "fileupload"}
        with open(file_path, "rb") as f:
            res = requests.post(url, data=data, files={"fileToUpload": f}, timeout=300)
        return res.text if res.status_code == 200 else None
    except: return None

# --- UI & ANIMATIONS ---
def get_status_animation(frame):
    frames = ["🌀", "⌛", "⚙️", "💎", "🚀", "🛰️", "🛸", "🔥"]
    return frames[frame % len(frames)]

def get_progress_bar(percent):
    full = int(percent / 10)
    return "🟩" * full + "⬜" * (10 - full) + f" **{percent}%**"

# --- KEYBOARDS ---
def get_verify_markup():
    markup = types.InlineKeyboardMarkup()
    for ch in REQUIRED_CHANNELS:
        markup.add(types.InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch[1:]}"))
    markup.add(types.InlineKeyboardButton("🔄 Verify & Unlock Engine", callback_data="verify_check"))
    return markup

def get_main_markup(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("👤 Developer", url="https://t.me/ShimulXD"),
               types.InlineKeyboardButton("📊 Global Stats", callback_data="global_stats"))
    if user_id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel"))
    return markup

def get_admin_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📢 Broadcast", callback_data="adm_bc"),
        types.InlineKeyboardButton("👥 User List (File)", callback_data="adm_list"),
        types.InlineKeyboardButton("🚫 Ban User", callback_data="adm_ban"),
        types.InlineKeyboardButton("✅ Unban User", callback_data="adm_unban"),
        types.InlineKeyboardButton("📊 Stats", callback_data="global_stats"),
        types.InlineKeyboardButton("❌ Close", callback_data="close_msg")
    )
    return markup

# --- START COMMAND ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    if is_banned(uid): 
        return bot.send_message(message.chat.id, "🚫 **You are banned from using this bot!**", parse_mode="Markdown")
    register_user(message.from_user)

    if not is_subscribed(uid):
        bot.send_photo(message.chat.id, IMAGE_URL, 
                       caption=f"👋 **Welcome, {message.from_user.first_name}!**\n\nTo use the **Blutter Pro Engine**, you must join our official channel and verify.",
                       reply_markup=get_verify_markup(), parse_mode="Markdown")
    else:
        show_welcome(message.chat.id, message.from_user.first_name, uid)

def show_welcome(chat_id, name, uid):
    welcome_text = (
        "╔════════════════════╗\n"
        "      🚀 **BLUTTER ENGINE PRO**\n"
        "╚════════════════════╝\n"
        f"🔹 **Status:** `Online` ✅\n"
        f"🔹 **Load:** `{active_dumps}/{CONCURRENCY_LIMIT}`\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📥 **Send me your .zip file** containing:\n"
        "📂 `libflutter.so` & `libapp.so` \n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "✨ **High-Speed Metadata Recovery Engine.**"
    )
    bot.send_photo(chat_id, IMAGE_URL, caption=welcome_text, reply_markup=get_main_markup(uid), parse_mode="Markdown")

# --- CALLBACK HANDLERS ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    uid = call.from_user.id
    
    if call.data == "verify_check":
        if is_subscribed(uid):
            bot.delete_message(call.message.chat.id, call.message.message_id)
            show_welcome(call.message.chat.id, call.from_user.first_name, uid)
        else: bot.answer_callback_query(call.id, "❌ Join the channel first!", show_alert=True)
            
    elif call.data == "global_stats":
        total = users_col.count_documents({})
        banned = banned_col.count_documents({})
        bot.answer_callback_query(call.id, f"📊 Stats: {total} Users | {banned} Banned", show_alert=True)
        
    elif call.data == "admin_panel" and uid == ADMIN_ID:
        bot.send_message(call.message.chat.id, "⚙️ **Supreme Admin Dashboard**", reply_markup=get_admin_markup(), parse_mode="Markdown")

    elif call.data == "adm_list" and uid == ADMIN_ID:
        # Generate User List as a file to handle large data perfectly
        users = users_col.find()
        file_path = "user_list.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("--- BLUTTER ENGINE USER LIST ---\n\n")
            for u in users:
                f.write(f"ID: {u.get('id')} | Name: {u.get('name')} | Username: @{u.get('username')}\n")
        
        with open(file_path, "rb") as f:
            bot.send_document(call.message.chat.id, f, caption="👥 **Total User Database List**", parse_mode="Markdown")
        os.remove(file_path)

    elif call.data == "adm_bc" and uid == ADMIN_ID:
        msg = bot.send_message(call.message.chat.id, "📩 **Send/Forward the message** for Broadcast.")
        bot.register_for_reply(msg, broadcast_exec)

    elif call.data == "adm_ban" and uid == ADMIN_ID:
        msg = bot.send_message(call.message.chat.id, "🚫 **Send the User ID to Ban:**")
        bot.register_for_reply(msg, ban_exec)

    elif call.data == "adm_unban" and uid == ADMIN_ID:
        msg = bot.send_message(call.message.chat.id, "✅ **Send the User ID to Unban:**")
        bot.register_for_reply(msg, unban_exec)

    elif call.data == "close_msg":
        bot.delete_message(call.message.chat.id, call.message.message_id)

# --- ADMIN ACTIONS ---
def broadcast_exec(message):
    users = users_col.find()
    s, f = 0, 0
    for u in users:
        try:
            bot.copy_message(u['id'], message.chat.id, message.message_id)
            s += 1
        except: f += 1
    bot.send_message(ADMIN_ID, f"📢 **Broadcast Completed!**\n✅ Success: {s}\n❌ Failed: {f}", parse_mode="Markdown")

def ban_exec(message):
    try:
        tid = int(message.text)
        banned_col.update_one({"id": tid}, {"$set": {"id": tid}}, upsert=True)
        bot.send_message(ADMIN_ID, f"🚫 **User {tid} has been banned!**", parse_mode="Markdown")
    except: bot.send_message(ADMIN_ID, "❌ **Invalid ID!**", parse_mode="Markdown")

def unban_exec(message):
    try:
        tid = int(message.text)
        banned_col.delete_one({"id": tid})
        bot.send_message(ADMIN_ID, f"✅ **User {tid} has been unbanned!**", parse_mode="Markdown")
    except: bot.send_message(ADMIN_ID, "❌ **Invalid ID!**", parse_mode="Markdown")

# --- CORE DUMPING ENGINE ---
@bot.message_handler(content_types=['document'])
def handle_dump(message):
    global active_dumps
    uid_id = message.from_user.id
    register_user(message.from_user)
    
    if is_banned(uid_id) or not is_subscribed(uid_id): return
    if not message.document.file_name.endswith('.zip'):
        return bot.reply_to(message, "❌ **Error:** Send a `.zip` file.", parse_mode="Markdown")

    if active_dumps >= CONCURRENCY_LIMIT and uid_id != ADMIN_ID:
        return bot.reply_to(message, "⚠️ **Server Load Full!** Wait a minute.", parse_mode="Markdown")

    active_dumps += 1
    uid = str(message.chat.id)
    work_dir, out_dir = f"work_{uid}", f"out_{uid}"
    shutil.rmtree(work_dir, ignore_errors=True)
    os.makedirs(work_dir)

    status_msg = bot.reply_to(message, "🛰 **Initializing Engine...**", parse_mode="Markdown")

    try:
        # Step 1: Downloading Animation
        for i in range(10, 101, 30):
            ani = get_status_animation(i//10)
            bot.edit_message_text(f"{ani} **Downloading File...**\n{get_progress_bar(i)}", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            time.sleep(0.3)
        
        file_info = bot.get_file(message.document.file_id)
        url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
        with requests.get(url, stream=True) as r:
            with open(f"{work_dir}/input.zip", 'wb') as f: shutil.copyfileobj(r.raw, f)

        # Step 2: Extraction
        bot.edit_message_text("📂 **Extracting Resources...**\n`Fast-Mode Active` ⚡", message.chat.id, status_msg.message_id, parse_mode="Markdown")
        with zipfile.ZipFile(f"{work_dir}/input.zip", 'r') as z: z.extractall(work_dir)

        # Step 3: Dumping (Keep Original Logic)
        if not os.path.exists('blutter_src'):
            subprocess.run("git clone https://github.com/AbhiTheModder/blutter-termux.git blutter_src", shell=True)
        
        os.chdir('blutter_src')
        subprocess.run("find . -type f -exec sed -i 's/std::format/fmt::format/g' {} +", shell=True)
        
        start_t = time.time()
        process = subprocess.Popen(f"python3 blutter.py ../{work_dir} ../{out_dir}", shell=True)
        
        frame = 0
        while process.poll() is None:
            elapsed = int(time.time() - start_t)
            ani = get_status_animation(frame)
            bot.edit_message_text(f"{ani} **Dumping in Progress...**\n`Elapsed: {elapsed}s` ⏱\n`Status: Reconstructing Metadata` 🛠", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            frame += 1
            time.sleep(4)
        os.chdir('..')

        # Step 4: Finalize
        if os.path.exists(out_dir) and any(os.scandir(out_dir)):
            res_zip = f"Dump_{uid}.zip"
            shutil.make_archive(res_zip.replace('.zip',''), 'zip', out_dir)
            f_size = os.path.getsize(res_zip) / (1024 * 1024)

            if f_size > 49.0:
                bot.edit_message_text(f"☁️ **Size: {f_size:.1f}MB**\n`Uploading to Cloud...` 🚀", message.chat.id, status_msg.message_id, parse_mode="Markdown")
                link = upload_to_catbox(res_zip)
                if link:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("📥 Download Result", url=link))
                    bot.send_message(message.chat.id, f"✅ **Dump Success!**\n⏱ Time: `{int(time.time()-start_t)}s`", reply_markup=markup, parse_mode="Markdown")
                else: bot.edit_message_text("❌ **Cloud Upload Failed.**", message.chat.id, status_msg.message_id, parse_mode="Markdown")
            else:
                bot.edit_message_text("📤 **Uploading Result...**", message.chat.id, status_msg.message_id, parse_mode="Markdown")
                with open(res_zip, 'rb') as f:
                    bot.send_document(message.chat.id, f, caption=f"✅ **Dump Success!**\n⏱ Time: `{int(time.time()-start_t)}s`", parse_mode="Markdown")
            
            os.remove(res_zip)
            send_log(f"✅ Success: {message.from_user.first_name}")
        else:
            bot.edit_message_text("❌ **Dumping Failed!** Incorrect libs.", message.chat.id, status_msg.message_id, parse_mode="Markdown")

    except Exception as e:
        bot.edit_message_text(f"⚠️ **Engine Error:** `{e}`", message.chat.id, status_msg.message_id, parse_mode="Markdown")

    finally:
        active_dumps -= 1
        shutil.rmtree(work_dir, ignore_errors=True)
        if os.path.exists(out_dir): shutil.rmtree(out_dir)

# --- RUN ---
print("🚀 Bot is Online!")
send_log("🚀 **Blutter Bot Online with Advanced Admin Panel.**")
bot.infinity_polling()
