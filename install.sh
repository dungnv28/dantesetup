#!/usr/bin/env bash

# Author - akmaslov-dev
# Modified by ThienTranJP
# Simple script to setup dante socks proxy server
# Should work on Debian, Ubuntu and CentOS

# Check for bash shell
if readlink /proc/$$/exe | grep -qs "dash"; then
	echo "This script needs to be run with bash, not sh"
	exit 1
fi

# Checking for root permission
if [[ "$EUID" -ne 0 ]]; then
	echo "Sorry, but you need to run this script as root"
	exit 2
fi

# Checking for distro type (Debian, Ubuntu or CentOS)
if [[ -e /etc/debian_version ]]; then
	OStype=deb
elif [[ -e /etc/centos-release || -e /etc/redhat-release ]]; then
	OStype=centos
else
	echo "You should only run this installer on Debian, Ubuntu or CentOS"
	exit 3
fi

# Checking for previous installation with this script
if [[ -e /etc/sockd.conf ]]; then
    while : ; do
	clear
		echo "Dante socks proxy is already installed."
		echo " "
		echo "What do you want to do now?"
		echo "	1) Add new user for proxy"
		echo "	2) Remove an existing user"
		echo "	3) Completely remove Dante socks proxy server"
		echo "	4) Exit"
		read -p "Select an option [1-4]: " option
		case $option in
			1)
			# Creating new user for proxy
			echo " "
			# Getting new Login
			read -p "Please enter the name for new proxy user: " -e -i proxyuser usernew
			echo " "
			# Getting new password for new user
			while true; do
				read -s -p "Now we need a VERY, VERY STRONG PASSWORD for new proxy user: " passwordnew
				echo " "
				read -s -p "Please retype your password (again): " passwordnew2
				echo " "
				[ "$passwordnew" = "$passwordnew2" ] && break
				echo "Password and password confirmation does not match"
				echo " "
				echo "Please try again"
				echo " "
			done
			# Creating new proxy user
			useradd -M -s /usr/sbin/nologin -p "$(openssl passwd -1 "$passwordnew")" "$usernew"
			echo " "
			echo "New user added!"
			exit
			;;
			2)
			# Deleting an existing user
			read -p "Please enter the name of the user to delete: " deluser
			echo " "
			if getent passwd "$deluser" > /dev/null 2>&1; then
			    userdel "$deluser"
			    echo "User $deluser deleted!"
			else
			    echo "Cannot find user with this name!"
			fi
			exit
			;;
			3)
			echo " "
			read -p "Do you really want to remove Dante socks proxy server? [y/n]: " -e -i n REMOVE
			if [[ "$REMOVE" = 'y' ]]; then
				if [[ "$OStype" = 'deb' ]]; then
					# If deb based distro
					systemctl stop sockd
					update-rc.d -f sockd remove
					rm -f /etc/init.d/sockd
					rm -f /etc/sockd.conf
					rm -f /usr/sbin/sockd
					echo " "
					echo "Dante socks proxy server deleted!"
				else
					# If CentOS
					systemctl stop sockd
					systemctl disable sockd
					rm -f /etc/systemd/system/sockd.service
					rm -f /usr/sbin/sockd
					rm -f /etc/sockd.conf
					systemctl daemon-reload
					systemctl reset-failed
					# Checking for firewalld
					if pgrep firewalld > /dev/null; then
						delport="$(grep 'port =' /etc/sockd.conf | awk '{print $5}')"
						firewall-cmd --zone=public --remove-port="$delport"/tcp
						firewall-cmd --zone=public --remove-port="$delport"/udp
						firewall-cmd --runtime-to-permanent
						firewall-cmd --reload
					fi
					echo " "
					echo "Dante socks proxy server deleted!"
				fi
			else
				echo " "
				echo "Removal process aborted!"
			fi
			exit
			;;
			4)
			# Just exit this script
			exit;;
		esac
	done
else
	clear
	# Obtaining name for system LAN interface
	interface="$(ip -o -4 route show to default | awk '{print $5}')"
	# Getting default port for socks proxy service
	read -p "Please enter the port number for our proxy server:  " -e -i 1080 port
	echo " "

	# Getting the number of proxies to create
	read -p "Please enter the number of proxies to create: " -e numofproxy
	echo " "
	
	# Generate random username and password for each proxy
	for i in $(seq 1 $numofproxy); do
		user[$i]=$(openssl rand -base64 8 | tr -dc 'a-zA-Z' | head -c 8)
		password[$i]=$(openssl rand -base64 12 | tr -dc 'a-zA-Z0-9' | head -c 12)
	done

	# Installing minimal requirements
	if [[ "$OStype" = 'deb' ]]; then
		# If deb based distro
		apt-get update
		apt-get -y install openssl make gcc
	else
		# Else, the distro is CentOS
		yum -y install epel-release
		yum -y install openssl make gcc
	fi

	# Getting Dante 1.4.3
	wget https://www.inet.no/dante/files/dante-1.4.3.tar.gz
	# Unpacking
	tar xvfz dante-1.4.3.tar.gz && cd dante-1.4.3 || exit 4
	# Configuring Dante
	./configure \
	--prefix=/usr \
	--sysconfdir=/etc \
	--localstatedir=/var \
	--disable-client \
	--without-libwrap \
	--without-bsdauth \
	--without-gssapi \
	--without-krb5 \
	--without-upnp \
	--without-pam
	# Compiling Dante
	make && make install

	# Creating /etc/sockd.conf
	cat > /etc/sockd.conf <<-EOF
	internal: $interface port = $port
	external: $interface
	user.privileged: root
	user.unprivileged: nobody
	socksmethod: username
	logoutput: /var/log/sockd.log
	client pass {
		from: 0.0.0.0/0 to: 0.0.0.0/0
		log: error
		socksmethod: username
	}
	socks pass {
		from: 0.0.0.0/0 to: 0.0.0.0/0
		command: bind connect udpassociate
		log: error
		socksmethod: username
	}
	EOF

	# Creating new users for proxy
	for i in $(seq 1 $numofproxy); do
		useradd -M -s /usr/sbin/nologin "${user[$i]}"
		echo "${user[$i]}:${password[$i]}" | chpasswd
	done

	# Creating services
	if [[ "$OStype" = 'deb' ]]; then
		# Creating sockd daemon for Debian/Ubuntu
		cat > /etc/init.d/sockd <<-'EOF'
		#!/usr/bin/env bash
		### BEGIN INIT INFO
		# Provides:          sockd
		# Required-Start:    $remote_fs $syslog
		# Required-Stop:     $remote_fs $syslog
		# Default-Start:     2 3 4 5
		# Default-Stop:      0 1 6
		# Short-Description: Start the dante SOCKS server.
		# Description:       SOCKS (v4 and v5) proxy server daemon (sockd).
		#                    This server allows clients to connect to it and
		#                    request proxying of TCP or UDP network traffic
		#                    with extensive configuration possibilities.
		### END INIT INFO

		DAEMON=/usr/sbin/sockd
		DAEMON_ARGS="-D"
		PIDFILE=/var/run/sockd.pid
		NAME=sockd
		CONFFILE=/etc/sockd.conf

		. /lib/lsb/init-functions

		case "$1" in
		  start)
		    log_daemon_msg "Starting Dante SOCKS proxy server" "$NAME"
		    start-stop-daemon --start --quiet --pidfile $PIDFILE --exec $DAEMON -- $DAEMON_ARGS
		    log_end_msg $?
		    ;;
		  stop)
		    log_daemon_msg "Stopping Dante SOCKS proxy server" "$NAME"
		    start-stop-daemon --stop --quiet --pidfile $PIDFILE --name $NAME
		    log_end_msg $?
		    ;;
		  restart)
		    $0 stop
		    $0 start
		    ;;
		  status)
		    status_of_proc "$DAEMON" "$NAME"
		    ;;
		  *)
		    echo "Usage: $0 {start|stop|restart|status}"
		    exit 1
		    ;;
		esac

		exit 0
		EOF
		# Making sockd service executable
		chmod +x /etc/init.d/sockd
		# Updating rc.d
		update-rc.d sockd defaults
		# Enabling autostart for sockd daemon
		update-rc.d sockd enable
		# Starting sockd daemon
		/etc/init.d/sockd start
	else
		# Creating systemctl service for CentOS
		cat > /etc/systemd/system/sockd.service <<-'EOF'
		[Unit]
		Description=Dante Socks Proxy v1.4.3
		After=network.target

		[Service]
		Type=forking
		PIDFile=/var/run/sockd.pid
		ExecStart=/usr/sbin/sockd -D -f /etc/sockd.conf
		ExecReload=/bin/kill -HUP $MAINPID
		KillMode=process
		Restart=on-failure

		[Install]
		WantedBy=multi-user.target graphical.target
		EOF

		# Restarting systemctl daemon
		systemctl daemon-reload
		# Enabling autostart for sockd service
		systemctl enable sockd
		# Adding exceptions for firewalld if running
		if pgrep firewalld > /dev/null; then
			firewall-cmd --zone=public --add-port="$port"/tcp
			firewall-cmd --zone=public --add-port="$port"/udp
			firewall-cmd --runtime-to-permanent
			firewall-cmd --reload
		fi
		# Starting service
		systemctl start sockd
	fi

	# Output proxy information to a file
	hostname=$(hostname -I | awk '{print $1}')
	output_file=~/proxy_info.txt
	for i in $(seq 1 $numofproxy); do
		echo "$hostname:$port:${user[$i]}:${password[$i]}" >> "$output_file"
	done
	cat "$output_file"

	# Transfer the file to a remote machine (replace with your own details)
	remote_user="root"
	remote_host="192.168.0.196"
	remote_path="/root/"

	scp "$output_file" "$remote_user@$remote_host:$remote_path"

	# Print success message
	echo "All Done and Success by ThienTranJP"
fi
