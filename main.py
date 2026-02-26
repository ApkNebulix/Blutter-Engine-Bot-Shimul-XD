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
REQUIRED_CHANNELS = ["@ShimulXD"] # এখানে আপনার চ্যানেলের ইউজারনেম লিস্ট দিন

bot = telebot.TeleBot(TOKEN)

# --- HELPER FUNCTIONS ---
def is_subscribed(user_id):
    if not REQUIRED_CHANNELS: return True
    try:
        for channel in REQUIRED_CHANNELS:
            status = bot.get_chat_member(channel, user_id).status
            if status == 'left': return False
        return True
    except:
        return True # Error handling

def get_welcome_markup():
    markup = types.InlineKeyboardMarkup()
    if REQUIRED_CHANNELS:
        for ch in REQUIRED_CHANNELS:
            markup.add(types.InlineKeyboardButton(text=f"Join {ch}", url=f"https://t.me/{ch[1:]}"))
        markup.add(types.InlineKeyboardButton(text="✅ Verify Join", callback_data="verify"))
    return markup

@bot.message_handler(commands=['start'])
def welcome(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        bot.send_photo(message.chat.id, IMAGE_URL, 
                       caption=f"👋 **Welcome to Blutter Engine!**\n\nTo use this bot, you must join our channels first.",
                       parse_mode="Markdown", reply_markup=get_welcome_markup())
    else:
        bot.send_photo(message.chat.id, IMAGE_URL, 
                       caption=f"🚀 **Blutter Engine Online!**\n\nHello {message.from_user.first_name},\nI am ready to dump your Flutter apps.\n\n📥 **How to use:**\nJust send me a `.zip` file containing your `libflutter.so` and `libapp.so` files (usually found in `lib/arm64-v8a/`).",
                       parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "verify")
def verify_callback(call):
    if is_subscribed(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "✅ **Verification Successful!** Now send me your zip file.")
    else:
        bot.answer_callback_query(call.id, "❌ You haven't joined all channels yet!", show_alert=True)

@bot.message_handler(content_types=['document'])
def handle_dump(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(message, "❌ Please join the channel first!")
        return

    if not message.document.file_name.endswith('.zip'):
        bot.reply_to(message, "❌ Please send a valid `.zip` file.")
        return

    status_msg = bot.reply_to(message, "🛰 **Initializing...**", parse_mode="Markdown")
    
    # Setup working directories
    uid = str(message.chat.id)
    work_dir = f"work_{uid}"
    out_dir = f"out_{uid}"
    if os.path.exists(work_dir): shutil.rmtree(work_dir)
    os.makedirs(work_dir)

    try:
        # Download
        bot.edit_message_text("📥 **Downloading files...**", message.chat.id, status_msg.message_id, parse_mode="Markdown")
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        with open(f"{work_dir}/input.zip", 'wb') as f: f.write(downloaded)

        # Extract
        bot.edit_message_text("📂 **Extracting & Analyzing...**", message.chat.id, status_msg.message_id, parse_mode="Markdown")
        with zipfile.ZipFile(f"{work_dir}/input.zip", 'r') as z: z.extractall(work_dir)

        # Clone Engine
        if not os.path.exists('blutter_src'):
            bot.edit_message_text("⚙️ **Preparing Engine...**", message.chat.id, status_msg.message_id, parse_mode="Markdown")
            subprocess.run("git clone https://github.com/AbhiTheModder/blutter-termux.git blutter_src", shell=True)

        # DUMPING PROCESS
        bot.edit_message_text("🛠 **Dumping Flutter Data...**\n(This might take 2-5 mins for new versions)", message.chat.id, status_msg.message_id, parse_mode="Markdown")
        
        start_time = time.time()
        os.chdir('blutter_src')
        # Patching for GitHub Actions Environment
        subprocess.run("find . -type f -exec sed -i 's/std::format/fmt::format/g' {} +", shell=True)
        
        process = subprocess.run(f"python3 blutter.py ../{work_dir} ../{out_dir}", shell=True, capture_output=True, text=True)
        os.chdir('..')

        if os.path.exists(out_dir) and any(os.scandir(out_dir)):
            duration = round(time.time() - start_time, 2)
            bot.edit_message_text(f"✅ **Dump Finished in {duration}s!**\nPreparing to send...", message.chat.id, status_msg.message_id, parse_mode="Markdown")
            
            # Zip output
            result_zip = f"Blutter_Result_{uid}.zip"
            shutil.make_archive(result_zip.replace('.zip', ''), 'zip', out_dir)
            
            with open(result_zip, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"✅ **Dump Success!**\n👤 Admin: @ShimulXD\n⏱ Time: {duration}s", parse_mode="Markdown")
            
            os.remove(result_zip)
        else:
            bot.edit_message_text(f"❌ **Dump Failed!**\nEnsure libflutter.so and libapp.so are present in the zip.", message.chat.id, status_msg.message_id, parse_mode="Markdown")

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

    # Cleanup
    if os.path.exists(work_dir): shutil.rmtree(work_dir)
    if os.path.exists(out_dir): shutil.rmtree(out_dir)

bot.infinity_polling()
