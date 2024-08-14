import paramiko
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext

# Telegram bot token
TOKEN = "7174276062:AAELdJjrf0I7Lk7Bwh0LTgMveeL5SYDaqgY"

# VPS server details
VPS_HOST = "45.12.134.116"
VPS_USER = "root"
VPS_PASSWORD = "Eqi9KlVA6Mof"

# SSH connection setup
def ssh_connect():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD)
    return client

# Fetch live proxy list from Dante server config
def get_proxy_list():
    client = ssh_connect()
    stdin, stdout, stderr = client.exec_command("grep 'socksmethod: username' /etc/sockd.conf -A 2")
    proxy_list = stdout.read().decode().splitlines()
    client.close()
    return proxy_list

# Add new proxy user
def add_proxy_user(username, password):
    client = ssh_connect()
    command = f"sudo useradd -M -s /usr/sbin/nologin -p $(openssl passwd -1 {password}) {username}"
    client.exec_command(command)
    client.close()

# Delete proxy user
def delete_proxy_user(username):
    client = ssh_connect()
    command = f"sudo userdel {username}"
    client.exec_command(command)
    client.close()

# Menu States
ADDING_USER, DELETING_USER = range(2)

# Start command
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Chào mừng bạn đến với Proxy Manager Bot! Bạn có thể sử dụng các lệnh:\n"
                              "/list_proxies - Xem danh sách proxy\n"
                              "/add_proxy - Thêm một proxy user\n"
                              "/delete_proxy - Xóa một proxy user\n"
                              "/clear_proxies - Xóa toàn bộ cấu hình proxy")

# Get proxy list command
def list_proxies(update: Update, context: CallbackContext):
    proxies = get_proxy_list()
    if proxies:
        update.message.reply_text("\n".join(proxies))
    else:
        update.message.reply_text("Không tìm thấy proxy nào đang hoạt động.")

# Add proxy command
def add_proxy(update: Update, context: CallbackContext):
    update.message.reply_text("Vui lòng nhập username cho proxy user mới:")
    return ADDING_USER

def adding_user(update: Update, context: CallbackContext):
    username = update.message.text
    context.user_data['username'] = username
    update.message.reply_text("Vui lòng nhập mật khẩu cho proxy user mới:")
    return ADDING_USER

def adding_password(update: Update, context: CallbackContext):
    password = update.message.text
    username = context.user_data.get('username')
    if username:
        add_proxy_user(username, password)
        update.message.reply_text(f"Proxy user {username} đã được thêm thành công!")
    else:
        update.message.reply_text("Không có username hợp lệ. Quay lại menu chính.")
    return ConversationHandler.END

# Delete proxy command
def delete_proxy(update: Update, context: CallbackContext):
    update.message.reply_text("Vui lòng nhập username của proxy user cần xóa:")
    return DELETING_USER

def deleting_user(update: Update, context: CallbackContext):
    username = update.message.text
    if username:
        delete_proxy_user(username)
        update.message.reply_text(f"Proxy user {username} đã được xóa thành công!")
    else:
        update.message.reply_text("Không tìm thấy username. Quay lại menu chính.")
    return ConversationHandler.END

# Clear all proxies command
def clear_proxies(update: Update, context: CallbackContext):
    client = ssh_connect()
    client.exec_command("sudo rm -f /etc/sockd.conf")
    client.close()
    update.message.reply_text("Toàn bộ cấu hình proxy đã được xóa!")

# Back command
def back(update: Update, context: CallbackContext):
    update.message.reply_text("Bạn đã quay lại menu chính.")
    return ConversationHandler.END

# Main function to start the bot
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('add_proxy', add_proxy), CommandHandler('delete_proxy', delete_proxy)],
        states={
            ADDING_USER: [MessageHandler(Filters.text & ~Filters.command, adding_user)],
            DELETING_USER: [MessageHandler(Filters.text & ~Filters.command, deleting_user)],
        },
        fallbacks=[CommandHandler('back', back)]
    )

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("list_proxies", list_proxies))
    dp.add_handler(CommandHandler("clear_proxies", clear_proxies))
    dp.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
