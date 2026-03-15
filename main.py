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

def get_live_count():
    try:
        gap = datetime.now() - timedelta(minutes=30)
        return users_col.count_documents({"last_active": {"$gt": gap}})
    except: return 0

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

# --- UI & ANIMATION ---
def get_status_animation(frame):
    frames = ["🌀", "⌛", "⚙️", "💎", "🚀", "🛰️", "🛸", "🔥", "✨", "🌟"]
    return frames[frame % len(frames)]

def get_progress_bar(percent):
    full = int(percent / 10)
    return "🎬" * full + "📽️" * (10 - full) + f" {percent}%"

def get_random_tip():
    tips = [
        "💡 Tip: Make sure your zip contains both libflutter.so and libapp.so!",
        "💡 Tip: Larger files may take more time to process.",
        "💡 Tip: Use /help to see all available commands.",
        "💡 Tip: Join @ShimulXDModZ for latest updates!"
    ]
    import random
    return random.choice(tips)

# --- KEYBOARDS ---
def get_verify_markup():
    markup = types.InlineKeyboardMarkup()
    for ch in REQUIRED_CHANNELS:
        markup.add(types.InlineKeyboardButton(f"Join {ch} 📢", url=f"https://t.me/{ch[1:]}"))
    markup.add(types.InlineKeyboardButton("🔄 Verify & Unlock Engine", callback_data="verify_check"))
    return markup

def get_main_markup(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("👤 Developer", url="https://t.me/ShimulXD"),
               types.InlineKeyboardButton("📊 Global Stats", callback_data="global_stats"))
    markup.add(types.InlineKeyboardButton("📖 How to Use", callback_data="how_to_use"),
               types.InlineKeyboardButton("🛠 Support", url="https://t.me/ShimulXDModZ"))
    if user_id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("⚙️ Admin Dashboard", callback_data="admin_panel"))
    return markup

# --- COMMANDS ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    if is_banned(uid): 
        return bot.send_message(message.chat.id, "🚫 **You are banned from using this bot!**")
    register_user(message.from_user)

    if not is_subscribed(uid):
        bot.send_photo(message.chat.id, IMAGE_URL, 
                       caption=f"👋 **Welcome, {message.from_user.first_name}!**\n\nTo use the **Blutter Pro Engine**, you must join our official channel and verify.",
                       reply_markup=get_verify_markup(), parse_mode="Markdown")
    else:
        show_welcome(message.chat.id, message.from_user.first_name, uid)

@bot.message_handler(commands=['help'])
def help_cmd(message):
    help_text = (
        "📖 **Blutter Engine Pro - Usage Guide**\n\n"
        "1️⃣ Prepare a `.zip` file containing `libflutter.so` and `libapp.so`.\n"
        "2️⃣ Send the file directly to the bot.\n"
        "3️⃣ Wait for the engine to process (Animations will show progress).\n"
        "4️⃣ Download your result once finished.\n\n"
        "📜 **Commands:**\n"
        "/start - Restart the bot\n"
        "/help - Show this guide\n"
        "/myinfo - Check your profile"
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['myinfo'])
def myinfo_cmd(message):
    uid = message.from_user.id
    user_data = users_col.find_one({"id": uid})
    info = (
        f"👤 **User Info**\n"
        f"━━━━━━━━━━━━\n"
        f"🆔 ID: `{uid}`\n"
        f"📛 Name: {message.from_user.first_name}\n"
        f"🌐 Status: {'Member' if not uid == ADMIN_ID else 'Administrator'}\n"
        f"📅 Last Active: {user_data['last_active'].strftime('%Y-%m-%d %H:%M')}"
    )
    bot.reply_to(message, info, parse_mode="Markdown")

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
        live = get_live_count()
        bot.answer_callback_query(call.id, f"🌍 Stats: {total} Total Users | {live} Active Now", show_alert=True)

    elif call.data == "how_to_use":
        bot.send_message(call.message.chat.id, "💡 **How to use:** Just send your `.zip` file containing `libflutter.so` & `libapp.so`. The bot will automatically dump the metadata for you.")
        
    elif call.data == "admin_panel" and uid == ADMIN_ID:
        show_admin_panel(call.message.chat.id)

    elif call.data == "adm_users" and uid == ADMIN_ID:
        total = users_col.count_documents({})
        banned = banned_col.count_documents({})
        bot.send_message(call.message.chat.id, f"📊 **User Statistics**\n\n👥 Total: {total}\n🚫 Banned: {banned}\n🟢 Live: {get_live_count()}")

    elif call.data == "adm_bc" and uid == ADMIN_ID:
        msg = bot.send_message(call.message.chat.id, "📩 **Forward or send the message** you want to broadcast (Text/Photo/Video/File).")
        bot.register_for_reply(msg, broadcast_exec)

    elif call.data == "adm_ban" and uid == ADMIN_ID:
        msg = bot.send_message(call.message.chat.id, "🚫 Send the **User ID** you want to ban.")
        bot.register_for_reply(msg, ban_exec)

    elif call.data == "close_msg":
        bot.delete_message(call.message.chat.id, call.message.message_id)

# --- ADMIN FUNCTIONS ---
def show_admin_panel(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📢 Broadcast", callback_data="adm_bc"),
        types.InlineKeyboardButton("📊 User Stats", callback_data="adm_users"),
        types.InlineKeyboardButton("🚫 Ban User", callback_data="adm_ban"),
        types.InlineKeyboardButton("❌ Close", callback_data="close_msg")
    )
    bot.send_message(chat_id, "🛠 **Supreme Admin Dashboard**\nControl everything from here.", reply_markup=markup)

def broadcast_exec(message):
    users = users_col.find()
    success = 0
    failed = 0
    progress_msg = bot.send_message(ADMIN_ID, "🚀 **Broadcasting Started...**")
    
    for u in users:
        try:
            bot.copy_message(u['id'], message.chat.id, message.message_id)
            success += 1
        except:
            failed += 1
    
    bot.edit_message_text(f"✅ **Broadcast Finished!**\n\n🟢 Success: {success}\n🔴 Failed/Blocked: {failed}", 
                          ADMIN_ID, progress_msg.message_id)

def ban_exec(message):
    try:
        target_id = int(message.text)
        banned_col.update_one({"id": target_id}, {"$set": {"id": target_id, "time": datetime.now()}}, upsert=True)
        bot.send_message(ADMIN_ID, f"✅ User `{target_id}` has been banned.")
    except:
        bot.send_message(ADMIN_ID, "❌ Invalid ID.")

# --- WELCOME UI ---
def show_welcome(chat_id, name, uid):
    load = f"🟢 Low Load: {active_dumps}/5" if active_dumps < 3 else f"🟠 Heavy Load: {active_dumps}/5"
    welcome_text = (
        "╔════════════════════╗\n"
        "      🚀 **BLUTTER ENGINE PRO**\n"
        "╚════════════════════╝\n"
        f"🔹 **System Status:** `Online` ✅\n"
        f"🔹 **Current Load:** `{load}`\n"
        f"🔹 **Live Users:** `{get_live_count()}` 👥\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📥 **Drop your .zip file below**\n"
        "📂 Must contain: `libflutter.so` & `libapp.so` \n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "✨ **Powered by Blutter Engine v2.0**"
    )
    bot.send_photo(chat_id, IMAGE_URL, caption=welcome_text, reply_markup=get_main_markup(uid), parse_mode="Markdown")

# --- CORE DUMPING ENGINE (ANIMATED) ---
@bot.message_handler(content_types=['document'])
def handle_dump(message):
    global active_dumps
    uid_id = message.from_user.id
    register_user(message.from_user)
    
    if is_banned(uid_id) or not is_subscribed(uid_id): return
    if not message.document.file_name.endswith('.zip'):
        return bot.reply_to(message, "❌ **Error:** Only `.zip` files are supported.")

    if active_dumps >= CONCURRENCY_LIMIT and uid_id != ADMIN_ID:
        return bot.reply_to(message, "⚠️ **Server Busy!** All nodes are occupied. Please wait 1-2 mins.")

    active_dumps += 1
    uid = str(message.chat.id)
    work_dir, out_dir = f"work_{uid}", f"out_{uid}"
    shutil.rmtree(work_dir, ignore_errors=True)
    os.makedirs(work_dir)

    status_msg = bot.reply_to(message, "🛰 **Initializing Pro Engine...**", parse_mode="Markdown")

    try:
        # Step 1: Downloading
        for i in range(10, 101, 25):
            ani = get_status_animation(i//10)
            bot.edit_message_text(f"{ani} **📥 Downloading Assets...**\n{get_progress_bar(i)}\n_{get_random_tip()}_", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            time.sleep(0.4)
        
        file_info = bot.get_file(message.document.file_id)
        url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
        with requests.get(url, stream=True) as r:
            with open(f"{work_dir}/input.zip", 'wb') as f: shutil.copyfileobj(r.raw, f)

        # Step 2: Extracting
        bot.edit_message_text("📂 **Extracting Resources...**\n`Processing Bytecode...` ⚙️", message.chat.id, status_msg.message_id, parse_mode="Markdown")
        with zipfile.ZipFile(f"{work_dir}/input.zip", 'r') as z: z.extractall(work_dir)

        # Step 3: Dumping Logic
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
            bot.edit_message_text(f"{ani} **Dumping Core Logic...**\n`Elapsed: {elapsed}s` ⏱\n`Status: Reconstructing Classes` 🛠\n\n_{get_random_tip()}_", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            frame += 1
            time.sleep(3)
        os.chdir('..')

        # Step 4: Finalizing
        if os.path.exists(out_dir) and any(os.scandir(out_dir)):
            res_zip = f"Result_{uid}.zip"
            shutil.make_archive(res_zip.replace('.zip',''), 'zip', out_dir)
            f_size = os.path.getsize(res_zip) / (1024 * 1024)

            if f_size > 48.0:
                bot.edit_message_text(f"🚀 **Large File Detected ({f_size:.1f}MB)**\n`Uploading to Cloud...` ☁️", message.chat.id, status_msg.message_id)
                link = upload_to_catbox(res_zip)
                if link:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("📥 Download Result (Catbox)", url=link))
                    bot.send_message(message.chat.id, f"✅ **Dump Completed!**\n⏱ Time: `{int(time.time()-start_t)}s`", reply_markup=markup, parse_mode="Markdown")
                else: bot.edit_message_text("❌ Cloud Upload Failed.", message.chat.id, status_msg.message_id)
            else:
                bot.edit_message_text("📤 **Uploading Result...**", message.chat.id, status_msg.message_id)
                with open(res_zip, 'rb') as f:
                    bot.send_document(message.chat.id, f, caption=f"✅ **Success!**\n⏱ Time: `{int(time.time()-start_t)}s`")
            
            os.remove(res_zip)
            send_log(f"✅ Success: {message.from_user.first_name} dumped a file.")
        else:
            bot.edit_message_text("❌ **Dumping Failed!**\nEnsure the .zip has correct `libflutter.so` and `libapp.so`.", message.chat.id, status_msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"⚠️ **Engine Error:** `{str(e)[:100]}`", message.chat.id, status_msg.message_id)

    finally:
        active_dumps -= 1
        shutil.rmtree(work_dir, ignore_errors=True)
        if os.path.exists(out_dir): shutil.rmtree(out_dir)

# --- RUN BOT ---
print("🚀 Bot is Starting...")
send_log("🚀 Supreme Blutter Bot is now ONLINE!")
bot.infinity_polling()
