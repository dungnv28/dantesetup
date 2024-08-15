import paramiko
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext
import requests

# Telegram bot token
TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

# VPS server details
VPS_USER = "YOUR_VPS_USERNAME"
VPS_PASSWORD = "YOUR_VPS_PASSWORD"

# Function to get the VPS IP address
def get_vps_ip():
    return requests.get('https://api.ipify.org').text

VPS_HOST = get_vps_ip()

# SSH connection setup
def ssh_connect():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD)
    return client

# /setupserver command
async def setup_server(update: Update, context: CallbackContext):
    await update.message.reply_text("Please enter the port number for the proxy server:")
    return 1

async def setup_port(update: Update, context: CallbackContext):
    port = update.message.text
    context.user_data['port'] = port
    await update.message.reply_text("Please enter the number of proxies to create:")
    return 2

async def setup_num_proxies(update: Update, context: CallbackContext):
    num_proxies = update.message.text
    port = context.user_data['port']

    client = ssh_connect()
    command = f"wget https://raw.githubusercontent.com/dungnv28/dantesetup/main/install_limit.sh -O install_limit.sh && echo -e '{port}\n{num_proxies}\n' | bash install_limit.sh"
    stdin, stdout, stderr = client.exec_command(command)
    result = stdout.read().decode()

    # Save proxies to file and return the list
    command = "cat ~/proxy_info.txt"
    stdin, stdout, stderr = client.exec_command(command)
    proxy_list = stdout.read().decode().splitlines()

    await update.message.reply_text("Proxy setup complete:\n" + "\n".join(proxy_list))
    
    client.exec_command("reset")
    client.close()
    return ConversationHandler.END

# /list_proxies command
async def list_proxies(update: Update, context: CallbackContext):
    client = ssh_connect()
    stdin, stdout, stderr = client.exec_command("cat ~/proxy_info.txt")
    proxy_list = stdout.read().decode().splitlines()
    client.close()
    
    if proxy_list:
        await update.message.reply_text("\n".join(proxy_list))
    else:
        await update.message.reply_text("No proxies found.")

# /add_proxy command
async def add_proxy(update: Update, context: CallbackContext):
    await update.message.reply_text("Please enter the username for the new proxy user:")
    return 3

async def add_proxy_user(update: Update, context: CallbackContext):
    username = update.message.text
    context.user_data['username'] = username
    await update.message.reply_text("Please enter the password for the new proxy user:")
    return 4

async def add_proxy_password(update: Update, context: CallbackContext):
    password = update.message.text
    username = context.user_data.get('username')

    client = ssh_connect()
    command = f"echo -e '1\n{username}\n{password}\n' | bash install.sh"
    stdin, stdout, stderr = client.exec_command(command)

    # Append new proxy to the file
    command = f"echo '{VPS_HOST}:1080:{username}:{password}' >> ~/proxy_info.txt"
    client.exec_command(command)
    
    client.close()
    
    await update.message.reply_text(f"Proxy user {username} added successfully!")
    return ConversationHandler.END

# /delete_proxy command
async def delete_proxy(update: Update, context: CallbackContext):
    await update.message.reply_text("Please enter the name of the proxy user to delete:")
    return 5

async def delete_proxy_user(update: Update, context: CallbackContext):
    username = update.message.text

    client = ssh_connect()
    command = f"echo -e '2\n{username}\n' | bash install.sh"
    stdin, stdout, stderr = client.exec_command(command)

    # Remove proxy from file
    command = f"sed -i '/{username}/d' ~/proxy_info.txt"
    client.exec_command(command)
    
    client.close()
    
    await update.message.reply_text(f"Proxy user {username} deleted successfully!")
    return ConversationHandler.END

# /clearserver command
async def clearserver(update: Update, context: CallbackContext):
    await update.message.reply_text("Do you really want to remove Dante socks proxy server? Type 'yes' to confirm or 'no' to cancel.")
    return 6

async def confirm_clearserver(update: Update, context: CallbackContext):
    confirmation = update.message.text.lower()
    
    if confirmation == 'yes':
        client = ssh_connect()
        
        # Thực thi lệnh trên VPS để gỡ bỏ proxy server
        command = "wget https://raw.githubusercontent.com/dungnv28/dantesetup/main/install.sh -O install.sh && bash install.sh"
        stdin, stdout, stderr = client.exec_command(command)
        
        # Gửi phím '3' để chọn 'Completely remove Dante socks proxy server'
        stdin.write('3\n')
        stdin.flush()
        
        # Xác nhận gỡ bỏ proxy server bằng cách gửi 'y'
        stdin.write('y\n')
        stdin.flush()

        # Đợi quá trình hoàn thành
        stdout.channel.recv_exit_status()
        
        await update.message.reply_text("Dante socks proxy server has been successfully removed.")
        
        client.close()
    else:
        await update.message.reply_text("Operation cancelled. Removal process aborted!")
    
    return ConversationHandler.END

# Start command
async def start(update: Update, context: CallbackContext):
    start_message = (
        "Chào mừng bạn đến với Proxy Manager Bot!\n\n"
        "Dưới đây là các lệnh mà bạn có thể sử dụng:\n"
        "/setupserver - Thiết lập server proxy mới\n"
        "/list_proxies - Xem danh sách proxy hiện có\n"
        "/add_proxy - Thêm một proxy user mới\n"
        "/delete_proxy - Xóa một proxy user\n"
        "/clearserver - Xóa toàn bộ cấu hình server proxy\n"
        "/back - Quay lại menu chính\n\n"
        "Hãy chọn một lệnh để bắt đầu tương tác với bot!"
    )
    await update.message.reply_text(start_message)

# Main function to start the bot
def main():
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('setupserver', setup_server),
            CommandHandler('add_proxy', add_proxy),
            CommandHandler('delete_proxy', delete_proxy),
            CommandHandler('clearserver', clearserver)
        ],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_port)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_num_proxies)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_proxy_user)],
            4: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_proxy_password)],
            5: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_proxy_user)],
            6: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_clearserver)],
        },
        fallbacks=[CommandHandler('back', lambda u, c: ConversationHandler.END)]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list_proxies", list_proxies))
    application.add_handler(conv_handler)

    application.run_polling()

if __name__ == '__main__':
    main()
