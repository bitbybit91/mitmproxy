# Deploying mitmproxy with Tor Hidden Service on Ubuntu VPS

This guide provides step-by-step instructions for deploying mitmproxy with Tor hidden service support on an Ubuntu VPS.

## Quick Start

**Automated Installation:**

```bash
# Download the script
wget https://raw.githubusercontent.com/bitbybit91/mitmproxy/master/setup-tor-ubuntu.sh

# IMPORTANT: Review the script before running
less setup-tor-ubuntu.sh

# After reviewing, run with sudo
sudo bash setup-tor-ubuntu.sh
```

The script will automatically install and configure everything. Your .onion address will be displayed at the end.

**Manual Installation:** Follow the detailed steps below.

## Prerequisites

- Ubuntu 18.04, 20.04, or 22.04 LTS server
- Root or sudo access
- At least 1GB RAM
- Basic knowledge of command line operations

## Table of Contents

1. [System Preparation](#system-preparation)
2. [Installing Dependencies](#installing-dependencies)
3. [Installing Tor](#installing-tor)
4. [Installing mitmproxy](#installing-mitmproxy)
5. [Configuration](#configuration)
6. [Starting the Service](#starting-the-service)
7. [Accessing Your Hidden Service](#accessing-your-hidden-service)
8. [Security Hardening](#security-hardening)
9. [Troubleshooting](#troubleshooting)
10. [Monitoring and Logs](#monitoring-and-logs)

## System Preparation

### 1. Update System Packages

```bash
# Update package lists
sudo apt update

# Upgrade existing packages
sudo apt upgrade -y
```

### 2. Create a Dedicated User (Recommended)

```bash
# Create a user for mitmproxy
sudo adduser --system --group --home /opt/mitmproxy mitmproxy

# Add user to necessary groups
sudo usermod -aG sudo mitmproxy  # Only if you need sudo access
```

## Installing Dependencies

### 1. Install Python and Development Tools

```bash
# Install Python 3.8 or higher
sudo apt install -y python3 python3-pip python3-venv python3-dev

# Install build dependencies
sudo apt install -y build-essential libssl-dev libffi-dev

# Install git (for cloning repository)
sudo apt install -y git
```

### 2. Verify Python Installation

```bash
python3 --version  # Should be 3.8 or higher
pip3 --version
```

## Installing Tor

### 1. Install Tor from Official Repository

```bash
# Install dependencies
sudo apt install -y apt-transport-https

# Add Tor repository
sudo bash -c 'cat > /etc/apt/sources.list.d/tor.list <<EOF
deb https://deb.torproject.org/torproject.org $(lsb_release -sc) main
deb-src https://deb.torproject.org/torproject.org $(lsb_release -sc) main
EOF'

# Add GPG key
curl https://deb.torproject.org/torproject.org/A3C4F0F979CAA22CDBA8F512EE8CBC9E886DDD89.asc | sudo gpg --dearmor -o /usr/share/keyrings/tor-archive-keyring.gpg

# Update package list
sudo apt update

# Install Tor
sudo apt install -y tor deb.torproject.org-keyring
```

### 2. Verify Tor Installation

```bash
tor --version
```

### 3. Stop Default Tor Service

```bash
# Stop and disable default Tor service (we'll run our own instance)
sudo systemctl stop tor
sudo systemctl disable tor
```

## Installing mitmproxy

### 1. Clone the Repository

```bash
# Clone this repository
cd /opt
sudo git clone https://github.com/bitbybit91/mitmproxy.git
sudo chown -R mitmproxy:mitmproxy /opt/mitmproxy
```

### 2. Create Virtual Environment

```bash
# Switch to mitmproxy user
sudo su - mitmproxy

# Navigate to project directory
cd /opt/mitmproxy

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

### 3. Install mitmproxy

```bash
# Install mitmproxy with all dependencies
pip install -e .

# Verify installation
mitmweb --version
```

## Configuration

### 1. Create Configuration Directory

```bash
# Create config directory
mkdir -p ~/.mitmproxy
chmod 700 ~/.mitmproxy
```

### 2. Create Configuration File

Create a configuration file at `~/.mitmproxy/config.yaml`:

```yaml
# Basic proxy settings
listen_host: 127.0.0.1
listen_port: 8080

# Web interface settings
web_host: 127.0.0.1
web_port: 8081
web_open_browser: false

# Tor hidden service settings
tor_enabled: true
tor_data_dir: ~/.mitmproxy/tor
tor_control_port: 9051
tor_socks_port: 9050
tor_web_service: true
tor_proxy_service: false  # Set to true if you want proxy accessible via .onion

# SSL/TLS settings
ssl_insecure: false

# Logging
verbose: info
```

### 3. Set Proper Permissions

```bash
chmod 600 ~/.mitmproxy/config.yaml
```

## Starting the Service

### 1. Manual Start (Testing)

```bash
# Activate virtual environment if not already active
cd /opt/mitmproxy
source venv/bin/activate

# Start mitmweb with Tor support
mitmweb --set confdir=~/.mitmproxy --set tor_enabled=true --set web_open_browser=false
```

### 2. Create Systemd Service (Production)

Exit from mitmproxy user and create a systemd service file:

```bash
# Exit to root/sudo user
exit

# Create systemd service file
sudo nano /etc/systemd/system/mitmproxy-tor.service
```

Add the following content:

```ini
[Unit]
Description=mitmproxy Web Interface with Tor Hidden Service
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=mitmproxy
Group=mitmproxy
WorkingDirectory=/opt/mitmproxy
Environment="PATH=/opt/mitmproxy/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/opt/mitmproxy/venv/bin/mitmweb \
    --set confdir=/opt/mitmproxy/.mitmproxy \
    --set tor_enabled=true \
    --set web_open_browser=false \
    --set web_host=127.0.0.1 \
    --set web_port=8081 \
    --listen-host 127.0.0.1 \
    --listen-port 8080
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/mitmproxy/.mitmproxy

[Install]
WantedBy=multi-user.target
```

### 3. Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable mitmproxy-tor.service

# Start the service
sudo systemctl start mitmproxy-tor.service

# Check status
sudo systemctl status mitmproxy-tor.service
```

## Accessing Your Hidden Service

### 1. Get Your .onion Address

```bash
# Wait 30-60 seconds for Tor to generate the address
sleep 60

# View the onion address
sudo -u mitmproxy cat /opt/mitmproxy/.mitmproxy/tor/hidden_service_web/hostname
```

### 2. Access from Tor Browser

1. Download and install [Tor Browser](https://www.torproject.org/download/)
2. Open Tor Browser
3. Navigate to your .onion address (e.g., `http://abc123def456ghi.onion`)

### 3. Local Access (on the VPS)

If you need to access the web interface locally:

```bash
# Create SSH tunnel (from your local machine)
ssh -L 8081:127.0.0.1:8081 user@your-vps-ip

# Then access in your browser
# http://localhost:8081
```

## Security Hardening

### 1. Configure Firewall

```bash
# Install UFW if not installed
sudo apt install -y ufw

# Deny all incoming by default
sudo ufw default deny incoming

# Allow outgoing
sudo ufw default allow outgoing

# Allow SSH (IMPORTANT: Do this first!)
sudo ufw allow 22/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

**Note:** Do NOT open ports 8080, 8081, 9050, or 9051 in the firewall. The service should only be accessible via Tor.

### 2. Disable Password Authentication (Use SSH Keys)

```bash
# Edit SSH config
sudo nano /etc/ssh/sshd_config

# Set the following options:
# PasswordAuthentication no
# PermitRootLogin no
# PubkeyAuthentication yes

# Restart SSH
sudo systemctl restart sshd
```

### 3. Install Fail2Ban

```bash
# Install fail2ban
sudo apt install -y fail2ban

# Start and enable
sudo systemctl start fail2ban
sudo systemctl enable fail2ban
```

### 4. Keep System Updated

```bash
# Enable automatic security updates
sudo apt install -y unattended-upgrades

# Configure automatic updates
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

### 5. Secure Tor Data Directory

```bash
# Ensure proper permissions
sudo -u mitmproxy chmod 700 /opt/mitmproxy/.mitmproxy/tor
sudo -u mitmproxy chmod 700 /opt/mitmproxy/.mitmproxy/tor/hidden_service_web
```

## Troubleshooting

### Service Won't Start

```bash
# Check service status
sudo systemctl status mitmproxy-tor.service

# View recent logs
sudo journalctl -u mitmproxy-tor.service -n 50

# Check Tor logs
sudo -u mitmproxy cat /opt/mitmproxy/.mitmproxy/tor/notice.log
```

### Tor Not Installed Error

```bash
# Verify Tor installation
which tor
tor --version

# Reinstall if necessary
sudo apt install --reinstall tor
```

### Permission Denied Errors

```bash
# Fix ownership
sudo chown -R mitmproxy:mitmproxy /opt/mitmproxy

# Fix permissions
sudo -u mitmproxy chmod 700 /opt/mitmproxy/.mitmproxy
sudo -u mitmproxy chmod -R 700 /opt/mitmproxy/.mitmproxy/tor
```

### .onion Address Not Generated

```bash
# Check if Tor is running
ps aux | grep tor

# Check Tor configuration
sudo -u mitmproxy cat /opt/mitmproxy/.mitmproxy/tor/torrc

# Manually verify Tor can start
sudo -u mitmproxy tor -f /opt/mitmproxy/.mitmproxy/tor/torrc
```

### Port Already in Use

```bash
# Check what's using the port
sudo lsof -i :8080
sudo lsof -i :8081
sudo lsof -i :9050
sudo lsof -i :9051

# Kill process if necessary
sudo kill <PID>

# Or change ports in configuration
```

### Python Version Issues

```bash
# Check Python version
python3 --version

# If version is too old, install newer Python
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.9 python3.9-venv python3.9-dev

# Recreate virtual environment with new Python
python3.9 -m venv venv
```

## Monitoring and Logs

### View Service Logs

```bash
# Real-time logs
sudo journalctl -u mitmproxy-tor.service -f

# Last 100 lines
sudo journalctl -u mitmproxy-tor.service -n 100

# Logs from specific time
sudo journalctl -u mitmproxy-tor.service --since "1 hour ago"
```

### Check Tor Status

```bash
# Check if Tor process is running
ps aux | grep tor

# View Tor logs
sudo -u mitmproxy cat /opt/mitmproxy/.mitmproxy/tor/notice.log
```

### Monitor Resource Usage

```bash
# Install htop
sudo apt install -y htop

# Run htop
htop

# Or use top
top
```

### Check Disk Space

```bash
# Check disk usage
df -h

# Check mitmproxy directory size
du -sh /opt/mitmproxy/.mitmproxy
```

## Backup and Recovery

### Backup Hidden Service Keys

**IMPORTANT:** Backup your hidden service keys to preserve your .onion address!

```bash
# Create backup directory
mkdir -p ~/backups

# Backup hidden service keys
sudo -u mitmproxy tar -czf ~/backups/mitmproxy-tor-keys-$(date +%Y%m%d).tar.gz \
    /opt/mitmproxy/.mitmproxy/tor/hidden_service_web
```

### Restore from Backup

```bash
# Stop service
sudo systemctl stop mitmproxy-tor.service

# Restore keys
sudo -u mitmproxy tar -xzf ~/backups/mitmproxy-tor-keys-YYYYMMDD.tar.gz -C /

# Set permissions
sudo -u mitmproxy chmod -R 700 /opt/mitmproxy/.mitmproxy/tor/hidden_service_web

# Start service
sudo systemctl start mitmproxy-tor.service
```

## Updating mitmproxy

```bash
# Stop service
sudo systemctl stop mitmproxy-tor.service

# Switch to mitmproxy user
sudo su - mitmproxy

# Navigate to directory
cd /opt/mitmproxy

# Pull latest changes
git pull origin master

# Activate virtual environment
source venv/bin/activate

# Update dependencies
pip install -e .

# Exit mitmproxy user
exit

# Start service
sudo systemctl start mitmproxy-tor.service
```

## Additional Configuration Options

### Expose Proxy via Hidden Service

To make the proxy itself accessible via .onion address:

```yaml
# In ~/.mitmproxy/config.yaml
tor_proxy_service: true
```

Then retrieve the proxy .onion address:

```bash
sudo -u mitmproxy cat /opt/mitmproxy/.mitmproxy/tor/hidden_service_proxy/hostname
```

### Custom Tor Configuration

For advanced Tor configuration, you can modify the generated torrc file at:
`/opt/mitmproxy/.mitmproxy/tor/torrc`

### Authentication

To add basic authentication to the web interface:

```yaml
# In ~/.mitmproxy/config.yaml
proxyauth: "username:password"
```

## Security Best Practices

1. **Never expose web_host or listen_host to 0.0.0.0** - Always use 127.0.0.1
2. **Keep your .onion address private** - Share only with trusted parties
3. **Regularly update** - Keep both system and mitmproxy updated
4. **Monitor logs** - Regularly check for suspicious activity
5. **Backup keys** - Regularly backup your hidden service keys
6. **Use strong passwords** - If implementing authentication
7. **Limit access** - Use firewall rules to restrict access
8. **Secure SSH** - Use key-based authentication only

## Support and Resources

- [mitmproxy Documentation](https://docs.mitmproxy.org/)
- [Tor Project Documentation](https://www.torproject.org/docs/)
- [GitHub Issues](https://github.com/bitbybit91/mitmproxy/issues)

## License

This documentation is provided as-is. Use at your own risk.
