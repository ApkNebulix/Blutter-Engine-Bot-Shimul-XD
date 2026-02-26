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

# ডাটাবেস সিমুলেশন (সহজ রাখার জন্য ফাইল ব্যবহার করা হয়েছে)
DB_FILE = "bot_data.json"
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({"users": [], "banned": []}, f)

def load_data():
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

# ইউজার রেজিস্টার ফাংশন
def register_user(user_id):
    data = load_data()
    if user_id not in data["users"]:
        data["users"].append(user_id)
        save_data(data)

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
    except Exception:
        return True # এরর এড়াতে True রাখা হয়েছে

# --- MIDDLEWARE & SECURITY ---
@bot.message_handler(func=lambda m: m.from_user.id in load_data()["banned"])
def handle_banned(message):
    bot.reply_to(message, "🚫 **Access Denied!**\nYou are banned from using this bot.")

# --- ADMIN PANEL COMMANDS ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID: return
    data = load_data()
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
        f"🆔 **ID:** `{ADMIN_ID}`\n"
        f"👥 **Total Users:** `{len(data['users'])}` \n"
        f"🚫 **Banned:** `{len(data['banned'])}`"
    )
    bot.send_message(message.chat.id, admin_text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(commands=['userinfo'])
def get_user_info(message):
    if message.from_user.id != ADMIN_ID: return
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    
    info = (
        f"👤 **User Information**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔹 **Name:** `{target.first_name}`\n"
        f"🔹 **Username:** @{target.username if target.username else 'N/A'}\n"
        f"🔹 **Language:** `{target.language_code}`\n"
        f"🔹 **ID:** `{target.id}`\n"
        f"━━━━━━━━━━━━━━━━━━"
    )
    bot.reply_to(message, info, parse_mode="Markdown")

@bot.message_handler(commands=['ban'])
def ban_user(message):
    if message.from_user.id != ADMIN_ID: return
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        data = load_data()
        if target_id not in data["banned"]:
            data["banned"].append(target_id)
            save_data(data)
            bot.reply_to(message, f"✅ User `{target_id}` has been banned.")
    else:
        bot.reply_to(message, "❌ Please reply to a user's message to ban them.")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    if message.from_user.id != ADMIN_ID: return
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        data = load_data()
        if target_id in data["banned"]:
            data["banned"].remove(target_id)
            save_data(data)
            bot.reply_to(message, f"✅ User `{target_id}` has been unbanned.")
    else:
        bot.reply_to(message, "❌ Reply to a user to unban.")

@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    if message.from_user.id != ADMIN_ID: return
    if not message.reply_to_message:
        bot.reply_to(message, "❌ **Error:** Please reply to a message (text/photo/video) to broadcast it.")
        return
    
    data = load_data()
    success = 0
    fail = 0
    bot.send_message(message.chat.id, "🚀 **Starting Broadcast...**")
    
    for user_id in data["users"]:
        try:
            bot.copy_message(user_id, message.chat.id, message.reply_to_message.message_id)
            success += 1
            time.sleep(0.1) # টেলিগ্রাম লিমিট এড়াতে
        except:
            fail += 1
            
    bot.send_message(message.chat.id, f"📢 **Broadcast Completed!**\n\n✅ Success: {success}\n❌ Failed: {fail}")

# --- CALLBACK HANDLERS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    if call.data == "verify":
        if is_subscribed(call.from_user.id):
            bot.edit_message_caption("✅ **Verified Successfully!**\nYou can now send your zip files for dumping.", call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "❌ Join the channel first!", show_alert=True)
    
    elif call.data == "user_list":
        if call.from_user.id != ADMIN_ID: return
        data = load_data()
        user_text = "📜 **Bot User List:**\n\n"
        for idx, u_id in enumerate(data["users"][:50]): # প্রথম ৫০ জন দেখাবে
            user_text += f"{idx+1}. `{u_id}`\n"
        bot.send_message(call.message.chat.id, user_text, parse_mode="Markdown")

    elif call.data == "broadcast_info":
        bot.answer_callback_query(call.id, "Reply to any message with /broadcast", show_alert=True)
    
    elif call.data == "close_admin":
        bot.delete_message(call.message.chat.id, call.message.message_id)

# --- START & VERIFY ---
@bot.message_handler(commands=['start'])
def welcome(message):
    register_user(message.from_user.id)
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
        "      🚀 **BLUTTER ENGINE PRO**\n"
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

# --- DUMPING PROCESS (LOGIC UNCHANGED) ---
@bot.message_handler(content_types=['document'])
def start_dump_process(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(message, "⚠️ **Access Denied!** Join @ShimulXDModZ first.")
        return

    if not message.document.file_name.endswith('.zip'):
        bot.reply_to(message, "❌ **Error:** Please send a valid `.zip` file.")
        return

    uid = str(message.chat.id)
    work_dir, out_dir = f"work_{uid}", f"out_{uid}"
    if os.path.exists(work_dir): shutil.rmtree(work_dir)
    os.makedirs(work_dir)

    status_msg = bot.reply_to(message, "🛰 **Initializing Engine...**", parse_mode="Markdown")

    try:
        # Step 1: Download
        bot.send_chat_action(message.chat.id, 'upload_document')
        for i in range(10, 101, 30):
            ani = get_status_animation(i//25)
            bot.edit_message_text(f"{ani} **Downloading File...**\n{create_progress_bar(i)}", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            time.sleep(0.3)

        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        with open(f"{work_dir}/input.zip", 'wb') as f: f.write(downloaded)

        # Step 2: Extract
        bot.edit_message_text("📂 **Extracting Resources...**\n`Analyzing Bytecode...` ⚡", 
                              message.chat.id, status_msg.message_id, parse_mode="Markdown")
        with zipfile.ZipFile(f"{work_dir}/input.zip", 'r') as z: z.extractall(work_dir)

        # Step 3: Dumping (Logic Intact)
        if not os.path.exists('blutter_src'):
            subprocess.run("git clone https://github.com/AbhiTheModder/blutter-termux.git blutter_src", shell=True)
        
        os.chdir('blutter_src')
        subprocess.run("find . -type f -exec sed -i 's/std::format/fmt::format/g' {} +", shell=True)
        
        start_t = time.time()
        process = subprocess.Popen(f"python3 blutter.py ../{work_dir} ../{out_dir}", shell=True)
        
        while process.poll() is None:
            bot.send_chat_action(message.chat.id, 'typing')
            elapsed = int(time.time() - start_t)
            ani = get_status_animation(elapsed)
            bot.edit_message_text(f"{ani} **Dumping in Progress...**\n`Elapsed Time: {elapsed}s` ⏱\n`Status: Compiling C++ Core` 🛠", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            time.sleep(4)

        os.chdir('..')

        # Step 4: Finalizing
        if os.path.exists(out_dir) and any(os.scandir(out_dir)):
            bot.edit_message_text("📦 **Dumping Finished!**\n`Zipping output files...` 📤", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            
            res_zip = f"Blutter_Output_{uid}.zip"
            shutil.make_archive(res_zip.replace('.zip',''), 'zip', out_dir)
            
            bot.send_chat_action(message.chat.id, 'upload_document')
            with open(res_zip, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"✅ **Dump Success!**\n⏱ **Time Taken:** {int(time.time()-start_t)}s\n👤 **By:** @ShimulXDModZ", parse_mode="Markdown")
            os.remove(res_zip)
        else:
            bot.edit_message_text("❌ **Dumping Failed!**\nEnsure `libflutter.so` and `libapp.so` are in the zip root.", message.chat.id, status_msg.message_id)

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ **System Error:** `{str(e)}`")

    # Cleanup
    shutil.rmtree(work_dir, ignore_errors=True)
    if os.path.exists(out_dir): shutil.rmtree(out_dir)

bot.infinity_polling()
