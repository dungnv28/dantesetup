# -*- coding: utf-8 -*-
import paramiko
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext, CallbackQueryHandler

# Telegram bot token
TOKEN = "7563357449:AAHQVWeO8CpS714OFEJ1HTc6HxvGN7Pn4Ts"

# VPS server details
VPS_USER = "root"
VPS_PASSWORD = "5AvJ*Q9z+5AK"

# Function to get the VPS IP address
def get_vps_ip():
    try:
        return requests.get('https://api.ipify.org').text
    except requests.RequestException as e:
        return None

VPS_HOST = get_vps_ip()

# SSH connection setup
def ssh_connect():
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD)
        return client
    except Exception as e:
        return None

# Function to set bandwidth limit and monitor usage (5GB limit)
def setup_bandwidth_limit(client, username):
    limit_bytes = 5 * 1024 * 1024 * 1024  # 5GB in bytes
    command = f"tc qdisc add dev eth0 root handle 1: htb default 30 && "
    command += f"tc class add dev eth0 parent 1: classid 1:1 htb rate 200mbit ceil 200mbit && "
    command += f"tc class add dev eth0 parent 1:1 classid 1:{username} htb rate 200mbit ceil 200mbit && "
    command += f"iptables -A OUTPUT -m owner --uid-owner {username} -j ACCEPT && "
    command += f"iptables -t mangle -A OUTPUT -m owner --uid-owner {username} -j MARK --set-mark {username}"
    stdin, stdout, stderr = client.exec_command(command)
    return stdout.read().decode(), stderr.read().decode()

# Function to monitor bandwidth usage
def monitor_bandwidth_usage(client, username):
    limit_bytes = 5 * 1024 * 1024 * 1024  # 5GB in bytes
    command = f"iptables -t mangle -L OUTPUT -v -x | grep {username} | awk '{{print $2}}'"
    stdin, stdout, stderr = client.exec_command(command)
    used_bytes = int(stdout.read().decode())
    
    if used_bytes >= limit_bytes:
        disconnect_user(client, username)
        return f"User {username} has been disconnected after exceeding the 5GB limit."
    else:
        remaining_bytes = limit_bytes - used_bytes
        remaining_gb = remaining_bytes / (1024 * 1024 * 1024)
        return f"User {username} has {remaining_gb:.2f} GB remaining."

# Function to disconnect a user
def disconnect_user(client, username):
    command = f"iptables -D OUTPUT -m owner --uid-owner {username} -j ACCEPT"
    client.exec_command(command)

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
    if client:
        command = f"wget https://raw.githubusercontent.com/dungnv28/dantesetup/main/install_limit.sh -O install_limit.sh && echo -e '{port}\\n{num_proxies}\\n' | bash install_limit.sh"
        stdin, stdout, stderr = client.exec_command(command)
        result = stdout.read().decode()

        # Save proxies to file and return the list
        command = "cat ~/proxy_info.txt"
        stdin, stdout, stderr = client.exec_command(command)
        proxy_list = stdout.read().decode().splitlines()

        # Apply bandwidth limit for each user
        for user in proxy_list:
            setup_bandwidth_limit(client, user.split(":")[2])

        await update.message.reply_text("Proxy setup complete:\n" + "\n".join(proxy_list))
        
        client.exec_command("reset")
        client.close()
    else:
        await update.message.reply_text("Failed to connect to VPS. Please check the connection and try again.")

    return ConversationHandler.END

# /list_proxies command
async def list_proxies(update: Update, context: CallbackContext):
    client = ssh_connect()
    if client:
        stdin, stdout, stderr = client.exec_command("cat ~/proxy_info.txt")
        proxy_list = stdout.read().decode().splitlines()
        client.close()
        
        if proxy_list:
            await update.message.reply_text("\n".join(proxy_list))
        else:
            await update.message.reply_text("No proxies found.")
    else:
        await update.message.reply_text("Failed to connect to VPS.")

# /list_bandwidth command to show remaining bandwidth
async def list_bandwidth(update: Update, context: CallbackContext):
    client = ssh_connect()
    if client:
        command = "cat /etc/passwd | grep 'nologin' | awk -F: '{print $1}'"
        stdin, stdout, stderr = client.exec_command(command)
        users = stdout.read().decode().splitlines()
        results = []
        
        for user in users:
            result = monitor_bandwidth_usage(client, user)
            results.append(result)
        
        await update.message.reply_text("\n".join(results))
        client.close()
    else:
        await update.message.reply_text("Failed to connect to VPS.")

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
    if client:
        command = "wget https://raw.githubusercontent.com/dungnv28/dantesetup/main/install.sh -O install.sh && bash install.sh"
        stdin, stdout, stderr = client.exec_command(command)
        
        stdin.write('1\n')
        stdin.flush()
        stdin.write(f"{username}\n")
        stdin.flush()
        stdin.write(f"{password}\n")
        stdin.flush()
        stdin.write(f"{password}\n")
        stdin.flush()

        stdout.channel.recv_exit_status()

        # Append new proxy to the file
        command = f"echo '{VPS_HOST}:1080:{username}:{password}' >> ~/proxy_info.txt"
        client.exec_command(command)
        
        # Set bandwidth limit for the new user
        setup_bandwidth_limit(client, username)
        
        client.close()
        
        await update.message.reply_text(f"Proxy user {username} added successfully!")
    else:
        await update.message.reply_text("Failed to connect to VPS.")
    
    return ConversationHandler.END

# Function to delete a proxy
async def delete_proxy(update: Update, context: CallbackContext):
    await update.message.reply_text("Please enter the username of the proxy to delete:")
    return 5

async def delete_proxy_user(update: Update, context: CallbackContext):
    username = update.message.text

    client = ssh_connect()
    if client:
        # Remove user from system
        command = f"userdel {username} && sed -i '/{username}/d' ~/proxy_info.txt"
        stdin, stdout, stderr = client.exec_command(command)
        
        client.close()
        
        await update.message.reply_text(f"Proxy user {username} deleted successfully!")
    else:
        await update.message.reply_text("Failed to connect to VPS.")
    
    return ConversationHandler.END

# Function to clear the server
async def clearserver(update: Update, context: CallbackContext):
    await update.message.reply_text("Are you sure you want to clear all proxies? Type 'yes' to confirm:")
    return 6

async def confirm_clearserver(update: Update, context: CallbackContext):
    confirmation = update.message.text.lower()
    
    if confirmation == 'yes':
        client = ssh_connect()
        if client:
            # Remove all proxy users and clear proxy_info.txt
            command = "cat ~/proxy_info.txt | awk -F: '{print $3}' | xargs -I {} userdel {} && rm ~/proxy_info.txt"
            client.exec_command(command)
            client.close()

            await update.message.reply_text("All proxies have been cleared from the server.")
        else:
            await update.message.reply_text("Failed to connect to VPS.")
    else:
        await update.message.reply_text("Operation cancelled.")
    
    return ConversationHandler.END

# Main function to start the bot
async def start(update: Update, context: CallbackContext):
    start_message = (
        "Chào mừng bạn đến với Proxy Manager Bot!\n\n"
        "Dưới đây là các lệnh mà bạn có thể sử dụng:\n"
        "/setupserver - Thiết lập server proxy mới\n"
        "/list_proxies - Xem danh sách proxy hiện có\n"
        "/add_proxy - Thêm một proxy user mới\n"
        "/delete_proxy - Xóa một proxy user\n"
        "/list_bandwidth - Kiểm tra băng thông còn lại\n"
        "/clearserver - Xóa toàn bộ cấu hình server proxy\n"
        "/back - Quay lại menu chính\n\n"
        "Hãy chọn một lệnh để bắt đầu tương tác với bot!"
    )

    # Tạo các nút để người dùng lựa chọn
    keyboard = [
        [InlineKeyboardButton("Thiết lập server proxy", callback_data='setupserver')],
        [InlineKeyboardButton("Xem danh sách proxy", callback_data='list_proxies')],
        [InlineKeyboardButton("Thêm proxy user", callback_data='add_proxy')],
        [InlineKeyboardButton("Xóa proxy user", callback_data='delete_proxy')],
        [InlineKeyboardButton("Kiểm tra băng thông", callback_data='list_bandwidth')],
        [InlineKeyboardButton("Xóa toàn bộ server proxy", callback_data='clearserver')]
    ]

    # Tạo một đối tượng InlineKeyboardMarkup từ danh sách các nút
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Gửi thông điệp cùng với các nút tương tác
    await update.message.reply_text(start_message, reply_markup=reply_markup)

# Hàm xử lý khi người dùng bấm vào các nút
async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()  # Gửi xác nhận rằng bot đã nhận được yêu cầu
    
    # Dựa trên callback_data, gọi các hàm tương ứng
    if query.data == 'setupserver':
        await setup_server(query, context)
    elif query.data == 'list_proxies':
        await list_proxies(query, context)
    elif query.data == 'add_proxy':
        await add_proxy(query, context)
    elif query.data == 'delete_proxy':
        await delete_proxy(query, context)
    elif query.data == 'list_bandwidth':
        await list_bandwidth(query, context)
    elif query.data == 'clearserver':
        await clearserver(query, context)

# Cập nhật main để thêm button handler
def main():
    application = Application.builder().token(TOKEN).build()

    # Thêm các handler cho các lệnh
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list_proxies", list_proxies))
    application.add_handler(CommandHandler("list_bandwidth", list_bandwidth))
    
    # Thêm handler cho tương tác nút bấm
    application.add_handler(CallbackQueryHandler(button_handler))

    # Thêm ConversationHandler cho các lệnh cần tương tác nhiều bước
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

    application.add_handler(conv_handler)

    application.run_polling()

if __name__ == '__main__':
    main()
