import os
import telebot
import subprocess
import shutil
import zipfile
import time
import requests
from telebot import types

# --- CONFIGURATION ---
TOKEN = '8635303381:AAH41sv7OVHm7WWAOFzKr3h68Fk0v0j2EvQ'
ADMIN_ID = 8381570120
IMAGE_URL = "https://raw.githubusercontent.com/ApkNebulix/Daroid-AN/refs/heads/main/Img/apknebulix.jpg"
REQUIRED_CHANNELS = ["@ShimulXDModZ"]

bot = telebot.TeleBot(TOKEN)

# --- DATABASE SIMULATION (Files for persistence) ---
USER_DB = "users.txt"
BAN_DB = "banned.txt"

def save_user(user_id):
    if not os.path.exists(USER_DB): open(USER_DB, "w").close()
    with open(USER_DB, "r+") as f:
        users = f.read().splitlines()
        if str(user_id) not in users:
            f.write(str(user_id) + "\n")

def is_banned(user_id):
    if not os.path.exists(BAN_DB): return False
    with open(BAN_DB, "r") as f:
        return str(user_id) in f.read().splitlines()

# --- UI HELPERS ---
def create_progress_bar(percent):
    done = int(percent / 10)
    bar = "█" * done + "░" * (10 - done)
    return f"[{bar}] {percent}%"

def get_status_animation(frame):
    frames = ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"]
    return frames[frame % len(frames)]

def is_subscribed(user_id):
    try:
        for channel in REQUIRED_CHANNELS:
            status = bot.get_chat_member(channel, user_id).status
            if status in ['left', 'kicked']: return False
        return True
    except:
        return True

# --- MANDATORY JOIN DECORATOR ---
def check_all(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        bot.reply_to(message, "🚫 You are banned from using this bot.")
        return False
    if not is_subscribed(user_id):
        markup = types.InlineKeyboardMarkup()
        for ch in REQUIRED_CHANNELS:
            markup.add(types.InlineKeyboardButton(text="Join Channel 📢", url=f"https://t.me/{ch[1:]}"))
        markup.add(types.InlineKeyboardButton(text="🔄 Verify Membership", callback_data="verify"))
        bot.send_photo(message.chat.id, IMAGE_URL, 
                       caption="👋 **Access Denied!**\n\nYou must join our official channel to use the Blutter Pro Engine.",
                       parse_mode="Markdown", reply_markup=markup)
        return False
    return True

# --- WELCOME SCREEN ---
@bot.message_handler(commands=['start'])
def welcome(message):
    save_user(message.from_user.id)
    if not check_all(message): return
    
    caption = (
        f"🚀 **Blutter Engine Pro Online**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **User:** {message.from_user.first_name}\n"
        f"🆔 **ID:** `{message.from_user.id}`\n"
        f"🛰 **Status:** `Active` ✅\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📥 **Send a .zip file** containing your `libflutter.so` and `libapp.so` for high-speed dumping."
    )
    bot.send_photo(message.chat.id, IMAGE_URL, caption=caption, parse_mode="Markdown")

# --- ADMIN PANEL ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID: return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("🚫 Ban User", callback_data="admin_ban"),
        types.InlineKeyboardButton("✅ Unban User", callback_data="admin_unban")
    )
    bot.send_message(message.chat.id, "🛠 **Admin Control Panel**\nWelcome back, Master Shimul.", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def admin_callback(call):
    if call.from_user.id != ADMIN_ID: return
    
    if call.data == "admin_stats":
        users = len(open(USER_DB).readlines()) if os.path.exists(USER_DB) else 0
        bot.answer_callback_query(call.id, f"Total Users: {users}", show_alert=True)
        
    elif call.data == "admin_broadcast":
        msg = bot.send_message(call.message.chat.id, "Reply to this message with the Text or Photo you want to broadcast.")
        bot.register_next_step_handler(msg, perform_broadcast)
        
    elif call.data == "admin_ban":
        msg = bot.send_message(call.message.chat.id, "Send the User ID you want to Ban.")
        bot.register_next_step_handler(msg, lambda m: manage_user(m, "ban"))

    elif call.data == "admin_unban":
        msg = bot.send_message(call.message.chat.id, "Send the User ID you want to Unban.")
        bot.register_next_step_handler(msg, lambda m: manage_user(m, "unban"))

def perform_broadcast(message):
    if not os.path.exists(USER_DB): return
    with open(USER_DB, "r") as f:
        users = f.read().splitlines()
    
    count = 0
    for user in users:
        try:
            if message.content_type == 'text':
                bot.send_message(user, message.text)
            elif message.content_type == 'photo':
                bot.send_photo(user, message.photo[-1].file_id, caption=message.caption)
            count += 1
        except: pass
    bot.send_message(ADMIN_ID, f"📢 Broadcast finished. Sent to {count} users.")

def manage_user(message, action):
    target_id = message.text.strip()
    if action == "ban":
        with open(BAN_DB, "a") as f: f.write(target_id + "\n")
        bot.send_message(ADMIN_ID, f"🚫 User {target_id} has been Banned.")
    else:
        if os.path.exists(BAN_DB):
            with open(BAN_DB, "r") as f: lines = f.readlines()
            with open(BAN_DB, "w") as f:
                for line in lines:
                    if line.strip() != target_id: f.write(line)
        bot.send_message(ADMIN_ID, f"✅ User {target_id} has been Unbanned.")

# --- DUMPING LOGIC (Preserved & Enhanced) ---
@bot.message_handler(content_types=['document'])
def handle_docs(message):
    if not check_all(message): return
    if not message.document.file_name.endswith('.zip'):
        bot.reply_to(message, "❌ Invalid format. Please send a `.zip` file.")
        return

    uid = str(message.chat.id)
    work_dir, out_dir = f"work_{uid}", f"out_{uid}"
    if os.path.exists(work_dir): shutil.rmtree(work_dir)
    os.makedirs(work_dir)

    status_msg = bot.reply_to(message, "🛰 **Initializing Pro Engine...**", parse_mode="Markdown")

    try:
        # Chat Status: Typing...
        bot.send_chat_action(message.chat.id, 'typing')

        # 1. Download with Animation
        for i in range(0, 101, 25):
            ani = get_status_animation(i//25)
            bot.edit_message_text(f"{ani} **Downloading Data...**\n{create_progress_bar(i)}", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            time.sleep(0.5)

        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        with open(f"{work_dir}/input.zip", 'wb') as f: f.write(downloaded)

        # 2. Extraction
        bot.edit_message_text("📂 **Extracting Byte-code...**\n`Safe Mode: Enabled` 🛡", 
                              message.chat.id, status_msg.message_id, parse_mode="Markdown")
        with zipfile.ZipFile(f"{work_dir}/input.zip", 'r') as z: z.extractall(work_dir)
        
        # 3. Dumping (Preserved Logic)
        if not os.path.exists('blutter_src'):
            subprocess.run("git clone https://github.com/AbhiTheModder/blutter-termux.git blutter_src", shell=True)
        
        os.chdir('blutter_src')
        subprocess.run("find . -type f -exec sed -i 's/std::format/fmt::format/g' {} +", shell=True)
        
        start_t = time.time()
        process = subprocess.Popen(f"python3 blutter.py ../{work_dir} ../{out_dir}", shell=True)
        
        while process.poll() is None:
            bot.send_chat_action(message.chat.id, 'typing') # Keep typing status active
            elapsed = int(time.time() - start_t)
            ani = get_status_animation(elapsed)
            bot.edit_message_text(f"{ani} **Dumping Flutter Engine...**\n`Elapsed: {elapsed}s` ⏱\n`Status: Compiling C++ Core` 🛠", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            time.sleep(4)

        os.chdir('..')

        # 4. Success & Upload
        if os.path.exists(out_dir) and any(os.scandir(out_dir)):
            bot.send_chat_action(message.chat.id, 'upload_document')
            bot.edit_message_text("📦 **Compiling Results...**\n`Wrapping files into archive` 📤", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            
            res_zip = f"Blutter_Result_{uid}.zip"
            shutil.make_archive(res_zip.replace('.zip',''), 'zip', out_dir)
            
            with open(res_zip, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"✅ **Dump Finished Successfully!**\n\n👤 Admin: @ShimulXDModZ\n⏱ Time Taken: {int(time.time()-start_t)}s", parse_mode="Markdown")
            os.remove(res_zip)
        else:
            bot.edit_message_text("❌ **Dumping Error!**\n`Library Files not found inside zip.`", message.chat.id, status_msg.message_id)

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Engine Error: {str(e)}")

    shutil.rmtree(work_dir, ignore_errors=True)
    if os.path.exists(out_dir): shutil.rmtree(out_dir)

@bot.callback_query_handler(func=lambda call: call.data == "verify")
def verify_btn(call):
    if is_subscribed(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Membership Verified!", show_alert=True)
        welcome(call.message)
    else:
        bot.answer_callback_query(call.id, "❌ Join the channel first!", show_alert=True)

print("Blutter Pro Bot is running...")
bot.infinity_polling()
