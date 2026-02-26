import os
import telebot
import subprocess
import shutil
import zipfile
import requests

# --- CONFIGURATION ---
TOKEN = '8635303381:AAH41sv7OVHm7WWAOFzKr3h68Fk0v0j2EvQ'
ADMIN_ID = 8381570120
bot = telebot.TeleBot(TOKEN)

def banner():
    return """
💎 *Blutter Engine - Shimul XD* 💎
Status: Online 🚀
Powered by: GitHub Actions
    """

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        f"{banner()}\n"
        f"👤 *Admin:* Shimul XD\n"
        f"🆔 *Chat ID:* `{message.chat.id}`\n\n"
        "How to use:\n"
        "1. Send me a `.zip` file containing `libflutter.so` and `libapp.so`.\n"
        "2. I will automatically detect the version and dump it."
    )
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    if not message.document.file_name.endswith('.zip'):
        bot.reply_to(message, "❌ Please send a .zip file containing the lib files.")
        return

    msg = bot.reply_to(message, "⏳ *Downloading your file...*", parse_mode='Markdown')
    
    # Setup directories
    work_dir = f"work_{message.chat.id}"
    out_dir = f"out_{message.chat.id}"
    if os.path.exists(work_dir): shutil.rmtree(work_dir)
    if os.path.exists(out_dir): shutil.rmtree(out_dir)
    os.makedirs(work_dir)

    # Download file
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    zip_path = os.path.join(work_dir, "input.zip")
    
    with open(zip_path, 'wb') as f:
        f.write(downloaded_file)

    # Extract zip
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(work_dir)

    bot.edit_message_text("⚙️ *Compiling & Dumping Flutter Data...*\nThis might take a few minutes for new versions.", message.chat.id, msg.message_id, parse_mode='Markdown')

    try:
        # Clone Blutter if not exists
        if not os.path.exists('blutter-src'):
            subprocess.run("git clone https://github.com/AbhiTheModder/blutter-termux.git blutter-src", shell=True)
        
        # Run Blutter
        # Command: python3 blutter.py <lib_dir> <out_dir>
        os.chdir('blutter-src')
        result = subprocess.run(f"python3 blutter.py ../{work_dir} ../{out_dir}", shell=True, capture_output=True, text=True)
        os.chdir('..')

        if os.path.exists(out_dir) and os.listdir(out_dir):
            # Zip the output
            final_zip = f"Dump_{message.chat.id}.zip"
            shutil.make_archive(f"Dump_{message.chat.id}", 'zip', out_dir)
            
            with open(final_zip, 'rb') as f:
                bot.send_document(message.chat.id, f, caption="✅ *Dump Successful!* \nBy @ShimulXD", parse_mode='Markdown')
            os.remove(final_zip)
        else:
            bot.reply_to(message, f"❌ *Dump Failed!*\nError: {result.stderr[:500]}")

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")
    
    # Cleanup
    shutil.rmtree(work_dir)
    if os.path.exists(out_dir): shutil.rmtree(out_dir)

print("Bot is running...")
bot.infinity_polling()
