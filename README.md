# Dante socks proxy server

[![pipeline status](https://gitlab.com/akmaslov/dante-proxy-server/badges/master/pipeline.svg)](https://gitlab.com/akmaslov/dante-proxy-server/commits/master)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/akmaslov-dev/dante-proxy-server/blob/master/LICENSE.txt)

## Main Info

Scripts for automated `dante socks proxy server` installation

Versatile setup script for `Ubuntu`, `Debian` and `CentOS` releases

Dante socks proxy server version - `1.4.2`

Official Dante proxy server page - <https://www.inet.no/dante/>

____

## Install and configuration section

Run this code in your terminal and follow the instructions:

```bash
wget https://raw.githubusercontent.com/dungnv28/dantesetup/main/install.sh -O install.sh && bash install.sh
```

```bash
wget https://raw.githubusercontent.com/dungnv28/dantesetup/main/install_jinzoo2803.sh -O install_jinzoo2803.sh && bash install_jinzoo2803.sh
```

```bash
wget https://raw.githubusercontent.com/dungnv28/dantesetup/main/install_ubuntu.sh -O install_ubuntu.sh && bash install_ubuntu.sh
```

```bash
wget https://raw.githubusercontent.com/dungnv28/dantesetup/main/install_limit.sh -O install_limit.sh && bash install_limit.sh
```
____

## Useful tips and tricks

Manual sockd options for Ubuntu and Debian `start`,  `stop`, `restart`, `status`

```bash
/etc/init.d/{PARAM_HERE}
```

Manual sockd options for CentOS `start`,  `stop`, `restart`, `status`

```bash
service sockd {PARAM_HERE}
```

Port, interface, auth metod, ipv4\ipv6 support and other cool options contains here

```bash
/etc/sockd.conf
```
## Dưới đây là quy trình cài đặt con bot Telegram trên VPS Ubuntu Digital, với file Python được đặt tại /root và cấu hình để nó chạy như một service khởi động cùng hệ thống:

**1\. Cập nhật hệ thống**

Trước khi bắt đầu, hãy đảm bảo hệ thống của bạn được cập nhật:
```bash
sudo apt update && sudo apt upgrade -y
```
**2\. Cài đặt Python và pip**

Cài đặt Python 3 và các công cụ cần thiết:

```bash
sudo apt install python3 python3-pip -y
```

**3\. Tạo và cài đặt môi trường ảo (Virtual Environment)**

Tạo một môi trường ảo để cài đặt các gói Python mà không ảnh hưởng đến hệ thống chính:

```bash
sudo apt install python3-venv -y

python3 -m venv /root/proxy_env

source /root/proxy_env/bin/activate

```

**4\. Cài đặt các thư viện cần thiết**

Cài đặt các gói Python cần thiết cho bot:

```bash
pip install paramiko python-telegram-bot requests
```

**5\. Tạo file Python cho bot**

Tạo file Python cho bot trong thư mục /root:

```bash
nano /root/proxy_manager_bot.py
```

Dán mã nguồn hoàn chỉnh của bot vào file này, sau đó lưu và thoát (Ctrl + O để lưu, Ctrl + X để thoát).

**6\. Cấu hình bot thành service**

Tạo một service để bot chạy cùng hệ thống:

```bash
sudo nano /etc/systemd/system/proxy_manager_bot.service
```

Nội dung của file service như sau:
```bash

ini

Sao chép mã

\[Unit\]

Description=Proxy Manager Bot

After=network.target

\[Service\]

ExecStart=/root/proxy_env/bin/python3 /root/proxy_manager_bot.py

WorkingDirectory=/root

Restart=always

User=root

\[Install\]

WantedBy=multi-user.target

```

**  
ver2  
**

```bash

\[Unit\]

Description=Proxy Manager Bot

After=network.target

\[Service\]

ExecStart=/root/proxy_env/bin/python3 /root/proxy_manager_bot.py

WorkingDirectory=/root

Restart=always

User=root

Environment="PYTHONUNBUFFERED=1"

\[Install\]

WantedBy=multi-user.target

```

**_SSH Key_**_: Nếu bạn muốn root sử dụng SSH key từ /home/administrator/id_rsa, hãy đảm bảo root có quyền đọc. Nếu không, bạn nên sao chép key vào thư mục /root để tránh các vấn đề về quyền truy cập._

```bash

sudo cp /home/administrator/id_rsa /root/

sudo chmod 600 /root/id_rsa

```

<br/>Nếu bạn đang sử dụng một môi trường ảo, hãy chắc chắn rằng bạn đã kích hoạt nó bằng cách:  
```bash
source /root/proxy_env/bin/activate

pip3 install paramiko
```

**7\. Kích hoạt và khởi động service**

Tải lại daemon systemd, kích hoạt và khởi động service:

```bash
source /root/proxy_env/bin/activate
```

```bash
sudo systemctl daemon-reload
```

```bash
sudo systemctl enable proxy_manager_bot.service
```

```bash
sudo systemctl start proxy_manager_bot.service
```
**8\. Kiểm tra trạng thái service**

Kiểm tra xem bot đã chạy hay chưa:

```bash
sudo systemctl status proxy_manager_bot.service
```
Nếu mọi thứ được cài đặt đúng, bạn sẽ thấy trạng thái của bot là "active (running)".

**9\. Quản lý service**

- **Khởi động lại bot:**

```bash
sudo systemctl restart proxy_manager_bot.service
```
- **Dừng bot:**

```bash
sudo systemctl stop proxy_manager_bot.service
```
- **Kiểm tra nhật ký (log) của bot:**

```bash

sudo journalctl -u proxy_manager_bot.service -f
```

**10\. Khởi động lại VPS để kiểm tra**

Khởi động lại VPS để đảm bảo bot chạy tự động khi hệ thống khởi động lại:

```bash
sudo reboot
```

**11\. Xác nhận bot hoạt động sau khi khởi động lại**

Sau khi VPS khởi động lại, hãy kiểm tra xem bot có hoạt động không:

```bash
sudo systemctl status proxy_manager_bot.service
```
Với các bước trên, bot Telegram sẽ được cài đặt trên VPS Ubuntu và hoạt động như một service, tự động khởi động cùng hệ thống. Nếu bạn gặp bất kỳ vấn đề nào hoặc cần thêm hỗ trợ, hãy cho tôi biết!
