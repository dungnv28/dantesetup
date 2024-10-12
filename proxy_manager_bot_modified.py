import paramiko
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext

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

# Function to check if a user has exceeded the 5GB limit
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

# Function to disconnect a user if they exceed the limit
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
    application.add_handler(CommandHandler("list_bandwidth", list_bandwidth))
    application.add_handler(conv_handler)

    application.run_polling()

if __name__ == '__main__':
    main()
