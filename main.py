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
REQUIRED_CHANNELS = ["@ShimulXDModZ"] # নিশ্চিত করুন বট এই চ্যানেলে অ্যাডমিন আছে

bot = telebot.TeleBot(TOKEN)
BANNED_USERS = set()

# --- JOIN CHECKER FUNCTION ---
def is_subscribed(user_id):
    if user_id == ADMIN_ID: return True
    try:
        for channel in REQUIRED_CHANNELS:
            member = bot.get_chat_member(channel, user_id)
            if member.status in ['left', 'kicked']:
                return False
        return True
    except Exception as e:
        # যদি বট চ্যানেলে অ্যাডমিন না থাকে তবে এই এরর হতে পারে
        print(f"Sub Check Error: {e}")
        return False

# --- UI HELPERS ---
def create_progress_bar(percent):
    done = int(percent / 10)
    bar = "█" * done + "░" * (10 - done)
    return f"[{bar}] {percent}%"

def get_status_animation(frame):
    frames = ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"]
    return frames[frame % len(frames)]

# --- MIDDLEWARE / FILTER ---
@bot.message_handler(func=lambda m: not is_subscribed(m.from_user.id))
def force_join(message):
    markup = types.InlineKeyboardMarkup()
    for ch in REQUIRED_CHANNELS:
        markup.add(types.InlineKeyboardButton(text="Join Channel 📢", url=f"https://t.me/{ch[1:]}"))
    markup.add(types.InlineKeyboardButton(text="🔄 Verify Membership", callback_data="verify"))
    
    bot.send_photo(message.chat.id, IMAGE_URL, 
                   caption=f"👋 **Hey {message.from_user.first_name}!**\n\n⚠️ বটটি ব্যবহার করতে হলে আপনাকে অবশ্যই আমাদের চ্যানেলে জয়েন থাকতে হবে। জয়েন করে নিচের ভেরিফাই বাটনে ক্লিক করুন।",
                   parse_mode="Markdown", reply_markup=markup)

# --- CALLBACK HANDLER ---
@bot.callback_query_handler(func=lambda call: call.data == "verify")
def verify_callback(call):
    if is_subscribed(call.from_user.id):
        bot.edit_message_caption("✅ **ধন্যবাদ!** আপনি সফলভাবে ভেরিফাই করেছেন। এখন ফাইল পাঠান।", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ আপনি এখনো চ্যানেলে জয়েন করেননি!", show_alert=True)

# --- ADMIN PANEL & COMMANDS ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID: return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📢 Broadcast", callback_data="bc_start"),
        types.InlineKeyboardButton("🚫 Ban List", callback_data="ban_list")
    )
    bot.reply_to(message, "🛠 **Admin Control Panel**\nবট নিয়ন্ত্রণের জন্য নিচের অপশন ব্যবহার করুন।", reply_markup=markup)

@bot.message_handler(commands=['userinfo'])
def user_info(message):
    if message.from_user.id != ADMIN_ID: return
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        info = f"👤 **User Info:**\n\nName: `{user.first_name}`\nID: `{user.id}`\nUsername: @{user.username}"
        bot.reply_to(message, info, parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ এই কমান্ডটি কাজ করতে ইউজারের মেসেজে রিপ্লাই করুন।")

@bot.message_handler(commands=['ban'])
def ban(message):
    if message.from_user.id != ADMIN_ID: return
    if message.reply_to_message:
        uid = message.reply_to_message.from_user.id
        BANNED_USERS.add(uid)
        bot.reply_to(message, f"✅ User `{uid}` banned successfully.")

# --- BROADCAST SYSTEM ---
@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    if message.from_user.id != ADMIN_ID: return
    if message.reply_to_message:
        # রিপ্লাই করা মেসেজটি সবার কাছে পাঠাবে (টেক্সট, ফটো সব সহ)
        bot.reply_to(message, "⌛ ব্রডকাস্ট শুরু হচ্ছে...")
        # এখানে ইউজার লিস্টের জন্য ডেটাবেস প্রয়োজন, আপাতত ডেমো হিসেবে রিপ্লাই মেসেজ রি-সেন্ড সিস্টেম রাখা হয়েছে।
        bot.send_message(message.chat.id, "✅ ব্রডকাস্ট সম্পন্ন (ডেটাবেস ছাড়া শুধু রিপ্লাই টেস্টিং)।")

# --- START COMMAND ---
@bot.message_handler(commands=['start'])
def welcome(message):
    # (force_join ফাংশনটি অটোমেটিক সাবস্ক্রিপশন চেক করবে)
    welcome_text = (
        "🚀 **Blutter Engine Pro Active!**\n\n"
        "Status: `Ready to Dump` ✅\n"
        "Admin: @ShimulXDModZ\n\n"
        "📥 **নির্দেশনা:**\n"
        "আপনার `.zip` ফাইলটি পাঠান (যাতে `libflutter.so` এবং `libapp.so` আছে)।"
    )
    bot.send_photo(message.chat.id, IMAGE_URL, caption=welcome_text, parse_mode="Markdown")

# --- DUMPING PROCESS (ORIGINAL LOGIC) ---
@bot.message_handler(content_types=['document'])
def start_dump_process(message):
    if message.from_user.id in BANNED_USERS: return
    
    if not message.document.file_name.endswith('.zip'):
        bot.reply_to(message, "❌ Invalid format. Send a `.zip` file.")
        return

    uid = str(message.chat.id)
    work_dir, out_dir = f"work_{uid}", f"out_{uid}"
    if os.path.exists(work_dir): shutil.rmtree(work_dir)
    os.makedirs(work_dir)

    status_msg = bot.reply_to(message, "🛰 **Initializing Engine...**", parse_mode="Markdown")

    try:
        # Typing Status Start
        bot.send_chat_action(message.chat.id, 'typing')

        # 1. Download
        for i in range(0, 101, 25):
            ani = get_status_animation(i//25)
            bot.edit_message_text(f"{ani} **Downloading File...**\n{create_progress_bar(i)}", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            time.sleep(0.5)

        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        with open(f"{work_dir}/input.zip", 'wb') as f: f.write(downloaded)

        # 2. Extract
        bot.edit_message_text("📂 **Extracting Resources...**\n`Processing Byte Streams...` ⚡", 
                              message.chat.id, status_msg.message_id, parse_mode="Markdown")
        with zipfile.ZipFile(f"{work_dir}/input.zip", 'r') as z: z.extractall(work_dir)

        # 3. Dumping logic (Unchanged)
        if not os.path.exists('blutter_src'):
            subprocess.run("git clone https://github.com/AbhiTheModder/blutter-termux.git blutter_src", shell=True)
        
        bot.edit_message_text("⚙️ **Dumping Flutter Metadata...**\n`This takes 1-4 mins` ⏳", 
                              message.chat.id, status_msg.message_id, parse_mode="Markdown")
        
        os.chdir('blutter_src')
        subprocess.run("find . -type f -exec sed -i 's/std::format/fmt::format/g' {} +", shell=True)
        
        start_t = time.time()
        process = subprocess.Popen(f"python3 blutter.py ../{work_dir} ../{out_dir}", shell=True)
        
        while process.poll() is None:
            bot.send_chat_action(message.chat.id, 'typing') # টাইপিং স্ট্যাটাস ডাম্পিং চলাকালীন
            elapsed = int(time.time() - start_t)
            ani = get_status_animation(elapsed)
            bot.edit_message_text(f"{ani} **Dumping in Progress...**\n`Time Elapsed: {elapsed}s` ⏱\n`Status: Compiling C++ Core` 🛠", 
                                  message.chat.id, status_msg.message_id, parse_mode="Markdown")
            time.sleep(4)

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
            bot.edit_message_text("❌ **Dumping Failed!**\nCheck your files.", message.chat.id, status_msg.message_id)

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Error: {str(e)}")

    shutil.rmtree(work_dir, ignore_errors=True)
    if os.path.exists(out_dir): shutil.rmtree(out_dir)

bot.infinity_polling()
