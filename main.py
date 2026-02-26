import os
import telebot
import subprocess
import shutil
import zipfile
import time
import json
from telebot import types

# --- CONFIGURATION ---
TOKEN = '8635303381:AAH41sv7OVHm7WWAOFzKr3h68Fk0v0j2EvQ'
ADMIN_ID = 8381570120
IMAGE_URL = "https://raw.githubusercontent.com/ApkNebulix/Daroid-AN/refs/heads/main/Img/apknebulix.jpg"
REQUIRED_CHANNELS = ["@ShimulXDModZ"] 

bot = telebot.TeleBot(TOKEN)

# --- DATABASE (Local for Session) ---
# Note: GitHub Actions resets every 4 hours, so users/ban list will reset 
# unless you connect a real Database.
DB_FILE = "bot_data.json"
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({"users": [], "banned": []}, f)

def get_data():
    with open(DB_FILE, "r") as f: return json.load(f)

def save_data(data):
    with open(DB_FILE, "w") as f: json.dump(data, f)

def register_user(user_id, name):
    data = get_data()
    if user_id not in [u['id'] for u in data['users']]:
        data['users'].append({"id": user_id, "name": name})
        save_data(data)

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
    except Exception:
        return True # Default to True if channel error

# --- MIDDLEWARE CHECK ---
def access_denied(message):
    data = get_data()
    if message.from_user.id in data['banned']:
        bot.reply_to(message, "🚫 **Access Denied!** You are banned from using this bot.")
        return True
    if not is_subscribed(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        for ch in REQUIRED_CHANNELS:
            markup.add(types.InlineKeyboardButton(text="Join Channel 📢", url=f"https://t.me/{ch[1:]}"))
        markup.add(types.InlineKeyboardButton(text="🔄 Verify Membership", callback_data="verify"))
        bot.send_photo(message.chat.id, IMAGE_URL, 
                       caption="⚠️ **Subscription Required!**\n\nYou must join our official channels to use this bot.",
                       reply_markup=markup)
        return True
    return False

# --- COMMANDS ---

@bot.message_handler(commands=['start'])
def welcome(message):
    register_user(message.from_user.id, message.from_user.first_name)
    if access_denied(message): return

    caption = (
        f"🚀 **Welcome to Blutter Pro Engine!**\n\n"
        f"Hello `{message.from_user.first_name}`,\n"
        f"Status: `Authorized` ✅\n\n"
        f"I am a specialized Flutter Dumper. Send me a `.zip` file containing "
        f"`libflutter.so` and `libapp.so` to start."
    )
    bot.send_photo(message.chat.id, IMAGE_URL, caption=caption, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "verify")
def verify_user(call):
    if is_subscribed(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "✅ **Verified!** You can now use the bot.")
    else:
        bot.answer_callback_query(call.id, "❌ Join the channel first!", show_alert=True)

# --- ADMIN PANEL ---

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID: return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 Stats", callback_data="adm_stats"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="adm_bc"),
        types.InlineKeyboardButton("🚫 Ban User", callback_data="adm_ban"),
        types.InlineKeyboardButton("✅ Unban User", callback_data="adm_unban")
    )
    bot.send_message(message.chat.id, "⚙️ **Admin Control Panel**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
def admin_callbacks(call):
    if call.from_user.id != ADMIN_ID: return
    
    data = get_data()
    if call.data == "adm_stats":
        msg = f"📈 **Bot Statistics**\n\nTotal Users: {len(data['users'])}\nBanned: {len(data['banned'])}"
        bot.answer_callback_query(call.id, "Stats Loaded")
        bot.send_message(call.message.chat.id, msg)
        
    elif call.data == "adm_bc":
        msg = bot.send_message(call.message.chat.id, "📩 **Reply to this message** with the Text or Photo you want to broadcast.")
        bot.register_for_reply(msg, broadcast_handler)

    elif call.data == "adm_ban":
        msg = bot.send_message(call.message.chat.id, "Enter User ID to **Ban**:")
        bot.register_next_step_handler(msg, ban_handler)

    elif call.data == "adm_unban":
        msg = bot.send_message(call.message.chat.id, "Enter User ID to **Unban**:")
        bot.register_next_step_handler(msg, unban_handler)

def broadcast_handler(message):
    data = get_data()
    count = 0
    for user in data['users']:
        try:
            if message.content_type == 'text':
                bot.send_message(user['id'], message.text)
            elif message.content_type == 'photo':
                bot.send_photo(user['id'], message.photo[-1].file_id, caption=message.caption)
            count += 1
        except: pass
    bot.send_message(ADMIN_ID, f"✅ Broadcast sent to {count} users.")

def ban_handler(message):
    try:
        uid = int(message.text)
        data = get_data()
        if uid not in data['banned']:
            data['banned'].append(uid)
            save_data(data)
            bot.send_message(ADMIN_ID, f"🚫 User `{uid}` has been banned.")
    except: bot.send_message(ADMIN_ID, "❌ Invalid User ID.")

def unban_handler(message):
    try:
        uid = int(message.text)
        data = get_data()
        if uid in data['banned']:
            data['banned'].remove(uid)
            save_data(data)
            bot.send_message(ADMIN_ID, f"✅ User `{uid}` has been unbanned.")
    except: bot.send_message(ADMIN_ID, "❌ Invalid User ID.")

# --- CORE DUMPING LOGIC (KEEPING ORIGINAL) ---

@bot.message_handler(content_types=['document'])
def start_dump_process(message):
    if access_denied(message): return

    if not message.document.file_name.endswith('.zip'):
        bot.reply_to(message, "❌ Invalid format. Send a `.zip` file.")
        return

    uid = str(message.chat.id)
    work_dir, out_dir = f"work_{uid}", f"out_{uid}"
    if os.path.exists(work_dir): shutil.rmtree(work_dir)
    os.makedirs(work_dir)

    status_msg = bot.reply_to(message, "🛰 **Initializing Engine...**", parse_mode="Markdown")

    try:
        # 1. Download
        for i in range(0, 101, 25):
            bot.send_chat_action(message.chat.id, 'typing')
            bot.edit_message_text(f"{get_status_animation(i//25)} **Downloading...**\n{create_progress_bar(i)}", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            time.sleep(0.5)

        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        with open(f"{work_dir}/input.zip", 'wb') as f: f.write(downloaded)

        # 2. Extract
        bot.send_chat_action(message.chat.id, 'typing')
        bot.edit_message_text("📂 **Extracting Resources...**", message.chat.id, status_msg.message_id)
        with zipfile.ZipFile(f"{work_dir}/input.zip", 'r') as z: z.extractall(work_dir)

        # 3. Dumping
        if not os.path.exists('blutter_src'):
            subprocess.run("git clone https://github.com/AbhiTheModder/blutter-termux.git blutter_src", shell=True)
        
        os.chdir('blutter_src')
        subprocess.run("find . -type f -exec sed -i 's/std::format/fmt::format/g' {} +", shell=True)
        
        start_t = time.time()
        process = subprocess.Popen(f"python3 blutter.py ../{work_dir} ../{out_dir}", shell=True)
        
        # --- TYPING STATUS LOOP ---
        while process.poll() is None:
            bot.send_chat_action(message.chat.id, 'typing') # Keeps typing status active
            elapsed = int(time.time() - start_t)
            bot.edit_message_text(f"{get_status_animation(elapsed)} **Dumping In Progress...**\n`Elapsed: {elapsed}s` ⏱\n`Status: Compiling Core` 🛠", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            time.sleep(4) # Adjust for bot speed

        os.chdir('..')

        # 4. Success
        if os.path.exists(out_dir) and any(os.scandir(out_dir)):
            res_zip = f"Blutter_Output_{uid}.zip"
            shutil.make_archive(res_zip.replace('.zip',''), 'zip', out_dir)
            with open(res_zip, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"✅ **Dump Success!**\n⏱ Time: {int(time.time()-start_t)}s")
            os.remove(res_zip)
        else:
            bot.edit_message_text("❌ **Dumping Failed!** Check libs.", message.chat.id, status_msg.message_id)

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Error: {str(e)}")

    shutil.rmtree(work_dir, ignore_errors=True)
    if os.path.exists(out_dir): shutil.rmtree(out_dir)

bot.infinity_polling()
