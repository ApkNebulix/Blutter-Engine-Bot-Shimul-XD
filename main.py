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
REQUIRED_CHANNELS = ["@ShimulXDModZ"] # Updated Channel

bot = telebot.TeleBot(TOKEN)

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
            if status == 'left': return False
        return True
    except:
        return True

@bot.message_handler(commands=['start'])
def welcome(message):
    markup = types.InlineKeyboardMarkup()
    for ch in REQUIRED_CHANNELS:
        markup.add(types.InlineKeyboardButton(text="Join Channel 📢", url=f"https://t.me/{ch[1:]}"))
    markup.add(types.InlineKeyboardButton(text="🔄 Verify Membership", callback_data="verify"))

    if not is_subscribed(message.from_user.id):
        bot.send_photo(message.chat.id, IMAGE_URL, 
                       caption="👋 **Welcome to Blutter Pro Engine!**\n\nTo access the advanced dumping features, please join our official channel.",
                       parse_mode="Markdown", reply_markup=markup)
    else:
        bot.send_photo(message.chat.id, IMAGE_URL, 
                       caption="🚀 **Blutter Engine Pro Active!**\n\nStatus: `Ready to Dump` ✅\n\n📥 **Send your .zip file** (containing `libflutter.so` and `libapp.so`) to begin the high-speed process.",
                       parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "verify")
def verify_user(call):
    if is_subscribed(call.from_user.id):
        bot.edit_message_caption("✅ **Verified!** You can now send your zip files.", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ Join the channel first!", show_alert=True)

@bot.message_handler(content_types=['document'])
def start_dump_process(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(message, "⚠️ Join @ShimulXDModZ first!")
        return

    if not message.document.file_name.endswith('.zip'):
        bot.reply_to(message, "❌ Invalid format. Send a `.zip` file.")
        return

    uid = str(message.chat.id)
    work_dir, out_dir = f"work_{uid}", f"out_{uid}"
    if os.path.exists(work_dir): shutil.rmtree(work_dir)
    os.makedirs(work_dir)

    status_msg = bot.reply_to(message, "🛰 **Initializing Engine...**", parse_mode="Markdown")

    try:
        # 1. Download with Pseudo-Progress
        for i in range(0, 101, 25):
            ani = get_status_animation(i//25)
            bot.edit_message_text(f"{ani} **Downloading File...**\n{create_progress_bar(i)}", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            time.sleep(0.5)

        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        with open(f"{work_dir}/input.zip", 'wb') as f: f.write(downloaded)

        # 2. Extract Animation
        bot.edit_message_text("📂 **Extracting Resources...**\n`Processing Byte Streams...` ⚡", 
                              message.chat.id, status_msg.message_id, parse_mode="Markdown")
        with zipfile.ZipFile(f"{work_dir}/input.zip", 'r') as z: z.extractall(work_dir)
        time.sleep(1)

        # 3. Dumping with Live Timer Animation
        if not os.path.exists('blutter_src'):
            subprocess.run("git clone https://github.com/AbhiTheModder/blutter-termux.git blutter_src", shell=True)
        
        bot.edit_message_text("⚙️ **Dumping Flutter Metadata...**\n`This takes 1-4 mins for new versions` ⏳", 
                              message.chat.id, status_msg.message_id, parse_mode="Markdown")
        
        os.chdir('blutter_src')
        subprocess.run("find . -type f -exec sed -i 's/std::format/fmt::format/g' {} +", shell=True)
        
        # Start Dumping
        start_t = time.time()
        process = subprocess.Popen(f"python3 blutter.py ../{work_dir} ../{out_dir}", shell=True)
        
        # Live status update while dumping
        while process.poll() is None:
            elapsed = int(time.time() - start_t)
            ani = get_status_animation(elapsed)
            bot.edit_message_text(f"{ani} **Dumping in Progress...**\n`Time Elapsed: {elapsed}s` ⏱\n`Status: Compiling C++ Core` 🛠", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            time.sleep(3)

        os.chdir('..')

        # 4. Success & Upload
        if os.path.exists(out_dir) and any(os.scandir(out_dir)):
            bot.edit_message_text("📦 **Dumping Complete!**\n`Creating final archive...` 📥", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            
            res_zip = f"Blutter_Output_{uid}.zip"
            shutil.make_archive(res_zip.replace('.zip',''), 'zip', out_dir)
            
            with open(res_zip, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"✅ **Dumping Successful!**\n\n👤 Admin: @ShimulXDModZ\n⏱ Total Time: {int(time.time()-start_t)}s", parse_mode="Markdown")
            os.remove(res_zip)
        else:
            bot.edit_message_text("❌ **Dumping Failed!**\nCheck if `libflutter.so` and `libapp.so` are correct.", message.chat.id, status_msg.message_id)

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Error: {str(e)}")

    shutil.rmtree(work_dir, ignore_errors=True)
    if os.path.exists(out_dir): shutil.rmtree(out_dir)

bot.infinity_polling()
