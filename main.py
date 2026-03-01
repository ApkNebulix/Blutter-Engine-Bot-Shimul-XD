import os, telebot, subprocess, shutil, zipfile, time, requests, urllib.parse, threading
from telebot import types
from pymongo import MongoClient
from datetime import datetime, timedelta

# --- 100% SUPREME CONFIG ---
TOKEN = '8635303381:AAH41sv7OVHm7WWAOFzKr3h68Fk0v0j2EvQ'
ADMIN_ID = 8381570120
LOG_CHANNEL = "@BotControlPanel"
REQUIRED_CHANNELS = ["@ShimulXDModZ"]
IMAGE_URL = "https://raw.githubusercontent.com/ApkNebulix/Daroid-AN/refs/heads/main/Img/apknebulix.jpg"

bot = telebot.TeleBot(TOKEN, threaded=True, num_threads=10)

# --- DATABASE CONNECTION ---
try:
    encoded_pass = urllib.parse.quote_plus("@%aN%#404%App@")
    client = MongoClient(f"mongodb+srv://apknebulix_modz:{encoded_pass}@apknebulix.suopcnt.mongodb.net/?appName=ApkNebulix")
    db = client['BlutterSupreme']
    users_col = db['users']
    banned_col = db['banned']
except: print("❌ Database Connection Failed")

# --- GLOBAL TRACKING ---
active_dumps = 0
LOCK = threading.Lock()

# --- UTILITY FUNCTIONS ---
def send_log(text):
    try: bot.send_message(LOG_CHANNEL, f"📝 **System Log**\n━━━━━━━━━━━━━━\n{text}", parse_mode="Markdown")
    except: pass

def is_subscribed(user_id):
    if user_id == ADMIN_ID: return True
    try:
        for ch in REQUIRED_CHANNELS:
            status = bot.get_chat_member(ch, user_id).status
            if status in ['left', 'kicked']: return False
        return True
    except: return True

def get_progress_bar(percent):
    full = int(percent / 10)
    return "💎" * full + "🌑" * (10 - full) + f" {percent}%"

# --- UI COMPONENTS ---
def welcome_screen(user):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👤 Developer", url="https://t.me/ShimulXD"),
        types.InlineKeyboardButton("📊 Live Stats", callback_data="bot_stats")
    )
    if user.id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("⚙️ Admin Command Center", callback_data="admin_panel"))
    
    status = "🟢 Engine Online"
    caption = (
        "╔════════════════════╗\n"
        "      🚀 **BLUTTER SUPREME ENGINE**\n"
        "╚════════════════════╝\n"
        f"👤 **User:** `{user.first_name}`\n"
        f"🛡 **Status:** `{status}`\n"
        f"👥 **Users:** `{users_col.count_documents({})}`\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📥 **Send ZIP file containing:**\n"
        "🔹 `libflutter.so` & `libapp.so` \n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💎 **Powered By Blutter Pro 2.0**"
    )
    return caption, markup

# --- MESSAGE HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    user = message.from_user
    users_col.update_one({"id": user.id}, {"$set": {"name": user.first_name, "active": datetime.now()}}, upsert=True)
    
    if banned_col.find_one({"id": user.id}):
        return bot.reply_to(message, "🚫 **Access Denied.** You are blacklisted.")

    if not is_subscribed(user.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Join Channel", url="https://t.me/ShimulXDModZ"))
        markup.add(types.InlineKeyboardButton("✅ Verify & Start", callback_data="verify_me"))
        return bot.send_photo(message.chat.id, IMAGE_URL, caption="⚠️ **Verification Required!**\nPlease join our channel to unlock the engine.", reply_markup=markup)

    cap, murk = welcome_screen(user)
    bot.send_photo(message.chat.id, IMAGE_URL, caption=cap, reply_markup=murk, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if call.data == "verify_me":
        if is_subscribed(call.from_user.id):
            bot.delete_message(call.message.chat.id, call.message.message_id)
            start(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ Join @ShimulXDModZ first!", show_alert=True)
    
    elif call.data == "bot_stats":
        total = users_col.count_documents({})
        active = users_col.count_documents({"active": {"$gt": datetime.now() - timedelta(minutes=30)}})
        bot.answer_callback_query(call.id, f"Total Users: {total}\nActive (30m): {active}", show_alert=True)

    elif call.data == "admin_panel":
        if call.from_user.id != ADMIN_ID: return
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📢 Global Broadcast", callback_data="broadcast"),
            types.InlineKeyboardButton("🚫 Manage Bans", callback_data="manage_ban"),
            types.InlineKeyboardButton("🔄 Refresh Server", callback_data="refresh")
        )
        bot.edit_message_caption("🛠 **Supreme Admin Dashboard**", call.message.chat.id, call.message.message_id, reply_markup=markup)

# --- CORE PROCESSING (100% SUCCESS LOGIC) ---
@bot.message_handler(content_types=['document'])
def handle_dump(message):
    global active_dumps
    if not is_subscribed(message.from_user.id): return
    if not message.document.file_name.endswith('.zip'):
        return bot.reply_to(message, "❌ **Error:** Please send a `.zip` file.")

    with LOCK:
        if active_dumps >= 5:
            return bot.reply_to(message, "⚠️ **Server Capacity Full!**\nMax 5 concurrent dumps allowed. Wait 2 minutes.")
        active_dumps += 1

    uid = str(message.chat.id)
    work_dir = f"work_{uid}"
    out_dir = f"out_{uid}"
    
    bot.send_chat_action(message.chat.id, 'typing')
    status_msg = bot.reply_to(message, "🛰 **Supreme Engine Initializing...**", parse_mode="Markdown")

    try:
        # Step 1: Download
        bot.edit_message_text(f"📥 **Downloading...**\n{get_progress_bar(20)}", message.chat.id, status_msg.message_id)
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        os.makedirs(work_dir, exist_ok=True)
        zip_path = os.path.join(work_dir, "input.zip")
        with open(zip_path, 'wb') as f: f.write(downloaded)

        # Step 2: Extract & Verify
        bot.edit_message_text(f"📂 **Extracting & Verifying...**\n{get_progress_bar(40)}", message.chat.id, status_msg.message_id)
        with zipfile.ZipFile(zip_path, 'r') as z: z.extractall(work_dir)
        
        # Search for .so files deeply
        libapp = None
        libflutter = None
        for root, dirs, files in os.walk(work_dir):
            for file in files:
                if file == "libapp.so": libapp = os.path.join(root, file)
                if file == "libflutter.so": libflutter = os.path.join(root, file)

        if not libapp or not libflutter:
            raise Exception("Required files (`libapp.so` / `libflutter.so`) not found in ZIP.")

        # Step 3: Blutter Execute
        bot.edit_message_text(f"⚙️ **Processing Blutter Engine...**\n`Running C++ Decompilation` ⚡", message.chat.id, status_msg.message_id)
        
        # Absolute Paths for safety
        abs_work = os.path.abspath(work_dir)
        abs_out = os.path.abspath(out_dir)
        
        start_t = time.time()
        # রান করার আগে আউটপুট ফোল্ডার ক্লিন করা
        if os.path.exists(out_dir): shutil.rmtree(out_dir)
        
        # Blutter execution
        cmd = f"python3 blutter_src/blutter.py {os.path.dirname(libapp)} {abs_out}"
        process = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if os.path.exists(out_dir) and any(os.scandir(out_dir)):
            # Step 4: Finalizing Output
            res_zip = f"Supreme_Dump_{uid}.zip"
            shutil.make_archive(res_zip.replace('.zip',''), 'zip', out_dir)
            
            bot.send_chat_action(message.chat.id, 'upload_document')
            bot.edit_message_text(f"✅ **Dump Completed!**\n⏱ Time: {int(time.time()-start_t)}s\n📤 **Sending Result...**", message.chat.id, status_msg.message_id)
            
            with open(res_zip, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"💎 **Supreme Blutter Result**\n⏱ Time: `{int(time.time()-start_t)}s`", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("👤 Dev", url="t.me/ShimulXD")))
            
            send_log(f"✅ **Success!**\nUser: {message.from_user.first_name}\nID: `{message.from_user.id}`")
            os.remove(res_zip)
        else:
            send_log(f"❌ **Failed!**\nUser: {message.from_user.first_name}\nError: Engine couldn't generate output.")
            bot.edit_message_text(f"❌ **Dump Failed!**\nInternal Engine Error.\n`Log: Check your SO files compatibility.`", message.chat.id, status_msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"⚠️ **Error:** `{str(e)}`", message.chat.id, status_msg.message_id)
        send_log(f"⚠️ **Error!**\nUser: {message.from_user.id}\nMsg: {str(e)}")

    finally:
        with LOCK: active_dumps -= 1
        shutil.rmtree(work_dir, ignore_errors=True)
        shutil.rmtree(out_dir, ignore_errors=True)

# --- BROADCAST SYSTEM ---
def broadcast_step(message):
    users = users_col.find()
    count = 0
    for u in users:
        try:
            bot.copy_message(u['id'], message.chat.id, message.message_id)
            count += 1
        except: pass
    bot.send_message(ADMIN_ID, f"✅ Broadcast finished. Sent to {count} users.")

# --- INITIALIZATION ---
if __name__ == "__main__":
    send_log("🚀 **Blutter Pro Engine Started**\nStatus: Online 🟢")
    print("💎 Supreme Bot is Running...")
    bot.infinity_polling()
