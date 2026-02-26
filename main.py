import os
import telebot
import subprocess
import shutil
import zipfile
import time
from telebot import types

# --- CONFIGURATION ---
TOKEN = '8635303381:AAH41sv7OVHm7WWAOFzKr3h68Fk0v0j2EvQ'
ADMIN_ID = 8381570120
IMAGE_URL = "https://raw.githubusercontent.com/ApkNebulix/Daroid-AN/refs/heads/main/Img/apknebulix.jpg"
REQUIRED_CHANNELS = ["@ShimulXDModZ"]

bot = telebot.TeleBot(TOKEN)
BANNED_USERS = set() # অস্থায়ী মেমোরি, ডেটাবেস যুক্ত করলে স্থায়ী হবে।

# --- UI & HELPERS ---
def create_progress_bar(percent):
    done = int(percent / 10)
    bar = "█" * done + "░" * (10 - done)
    return f"[{bar}] {percent}%"

def get_status_animation(frame):
    frames = ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"]
    return frames[frame % len(frames)]

def is_subscribed(user_id):
    if user_id == ADMIN_ID: return True
    try:
        for channel in REQUIRED_CHANNELS:
            status = bot.get_chat_member(channel, user_id).status
            if status in ['left', 'kicked']: return False
        return True
    except Exception:
        return False # যদি বট চ্যানেলে অ্যাডমিন না থাকে তবে চেক কাজ করবে না

# --- MIDDLEWARE ---
@bot.message_handler(func=lambda m: m.from_user.id in BANNED_USERS)
def handle_banned(message):
    bot.reply_to(message, "🚫 **You are banned from using this bot!**")

# --- ADMIN PANEL COMMANDS ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID: return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 Stats", callback_data="stats"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="broadcast_prompt")
    )
    bot.send_message(message.chat.id, "🛠 **Admin Control Panel**\nManage your bot and users below:", reply_markup=markup)

@bot.message_handler(commands=['userinfo'])
def get_user_info(message):
    if message.from_user.id != ADMIN_ID: return
    if message.reply_to_message:
        u = message.reply_to_message.from_user
        info = f"👤 **User Info:**\n\n**Name:** `{u.first_name}`\n**ID:** `{u.id}`\n**Username:** @{u.username}"
        bot.reply_to(message, info, parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ Please reply to a user's message to get their info.")

@bot.message_handler(commands=['ban'])
def ban_user(message):
    if message.from_user.id != ADMIN_ID: return
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        BANNED_USERS.add(target_id)
        bot.reply_to(message, f"✅ User `{target_id}` has been banned.")
    else:
        bot.reply_to(message, "❌ Reply to a user to ban them.")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    if message.from_user.id != ADMIN_ID: return
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        BANNED_USERS.discard(target_id)
        bot.reply_to(message, f"✅ User `{target_id}` unbanned.")

# --- START & VERIFY ---
@bot.message_handler(commands=['start'])
def welcome(message):
    if not is_subscribed(message.from_user.id):
        markup = types.InlineKeyboardMarkup()
        for ch in REQUIRED_CHANNELS:
            markup.add(types.InlineKeyboardButton(text="Join Channel 📢", url=f"https://t.me/{ch[1:]}"))
        markup.add(types.InlineKeyboardButton(text="🔄 Verify Membership", callback_data="verify"))
        
        bot.send_photo(message.chat.id, IMAGE_URL, 
                       caption=f"👋 **Welcome {message.from_user.first_name}!**\n\n🛡 **Access Locked:** You must join our official channels to use the Blutter Pro Engine.",
                       parse_mode="Markdown", reply_markup=markup)
        return

    welcome_text = (
        "🚀 **Blutter Engine Pro - Active**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Status: `Ready to Dump` ✅\n"
        "Version: `v2.5 High-Speed` ⚡\n\n"
        "📥 **How to use:**\n"
        "Send a `.zip` file containing:\n"
        "└ `libflutter.so` & `libapp.so`\n\n"
        "🛠 **Features:** Auto-sed, C++ Core Dumping."
    )
    bot.send_photo(message.chat.id, IMAGE_URL, caption=welcome_text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "verify")
def verify_user(call):
    if is_subscribed(call.from_user.id):
        bot.edit_message_caption("✅ **Verified Successfully!**\nYou can now send your zip files for dumping.", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ You haven't joined the channel yet!", show_alert=True)

# --- DUMPING PROCESS ---
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

    # Status Message
    status_msg = bot.reply_to(message, "🛰 **Engine Initializing...**", parse_mode="Markdown")

    try:
        # 1. Download
        bot.send_chat_action(message.chat.id, 'upload_document')
        for i in range(0, 101, 25):
            ani = get_status_animation(i//25)
            bot.edit_message_text(f"{ani} **Downloading File...**\n{create_progress_bar(i)}", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            time.sleep(0.3)

        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        with open(f"{work_dir}/input.zip", 'wb') as f: f.write(downloaded)

        # 2. Extract
        bot.edit_message_text("📂 **Extracting Resources...**\n`Analyzing Bytecode...` ⚡", 
                              message.chat.id, status_msg.message_id, parse_mode="Markdown")
        with zipfile.ZipFile(f"{work_dir}/input.zip", 'r') as z: z.extractall(work_dir)

        # 3. Dumping (The Core Logic)
        if not os.path.exists('blutter_src'):
            subprocess.run("git clone https://github.com/AbhiTheModder/blutter-termux.git blutter_src", shell=True)
        
        os.chdir('blutter_src')
        subprocess.run("find . -type f -exec sed -i 's/std::format/fmt::format/g' {} +", shell=True)
        
        start_t = time.time()
        process = subprocess.Popen(f"python3 blutter.py ../{work_dir} ../{out_dir}", shell=True)
        
        # Typing Status & Live Timer
        while process.poll() is None:
            bot.send_chat_action(message.chat.id, 'typing') # টাইপিং স্ট্যাটাস শো করবে
            elapsed = int(time.time() - start_t)
            ani = get_status_animation(elapsed)
            bot.edit_message_text(f"{ani} **Dumping in Progress...**\n`Elapsed: {elapsed}s` ⏱\n`Status: Compiling C++ Core` 🛠", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            time.sleep(4) # রিকোয়েস্ট লিমিট এড়াতে ৪ সেকেন্ড পর পর আপডেট

        os.chdir('..')

        # 4. Finalizing
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
