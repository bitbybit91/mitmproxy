#!/bin/bash
#
# Quick setup script for mitmproxy with Tor hidden service on Ubuntu
# Usage: sudo bash setup-tor-ubuntu.sh
#

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    print_error "Please run as root (use sudo)"
    exit 1
fi

print_status "Starting mitmproxy with Tor hidden service setup..."

# Update system
print_status "Updating system packages..."
apt update
apt upgrade -y

# Install Python and dependencies
print_status "Installing Python and build dependencies..."
apt install -y python3 python3-pip python3-venv python3-dev \
    build-essential libssl-dev libffi-dev git \
    apt-transport-https curl

# Install Tor
print_status "Installing Tor..."

# Add Tor repository
cat > /etc/apt/sources.list.d/tor.list <<EOF
deb https://deb.torproject.org/torproject.org $(lsb_release -sc) main
deb-src https://deb.torproject.org/torproject.org $(lsb_release -sc) main
EOF

# Add GPG key
curl --fail-with-body https://deb.torproject.org/torproject.org/A3C4F0F979CAA22CDBA8F512EE8CBC9E886DDD89.asc | \
    gpg --dearmor -o /usr/share/keyrings/tor-archive-keyring.gpg || {
    print_error "Failed to download Tor GPG key"
    exit 1
}

# Update and install
apt update
apt install -y tor deb.torproject.org-keyring

# Stop default Tor service
systemctl stop tor
systemctl disable tor

print_status "Tor installed successfully"

# Create mitmproxy user
if ! id -u mitmproxy >/dev/null 2>&1; then
    print_status "Creating mitmproxy user..."
    adduser --system --group --home /opt/mitmproxy mitmproxy
else
    print_warning "User 'mitmproxy' already exists"
fi

# Clone or update repository
if [ -d "/opt/mitmproxy" ]; then
    print_warning "Directory /opt/mitmproxy already exists, updating..."
    cd /opt/mitmproxy
    sudo -u mitmproxy git pull || print_warning "Git pull failed, continuing..."
else
    print_status "Cloning mitmproxy repository..."
    cd /opt
    # Using HTTPS for better compatibility
    git clone https://github.com/bitbybit91/mitmproxy.git || {
        print_error "Failed to clone repository"
        exit 1
    }
    chown -R mitmproxy:mitmproxy /opt/mitmproxy
fi

# Create virtual environment and install
print_status "Setting up Python virtual environment..."
cd /opt/mitmproxy
sudo -u mitmproxy python3 -m venv venv
sudo -u mitmproxy bash -c "source venv/bin/activate && pip install --upgrade pip setuptools wheel"
sudo -u mitmproxy bash -c "source venv/bin/activate && pip install -e ."

# Create configuration directory
print_status "Creating configuration directory..."
sudo -u mitmproxy mkdir -p /opt/mitmproxy/.mitmproxy
sudo -u mitmproxy chmod 700 /opt/mitmproxy/.mitmproxy

# Copy example configuration
if [ ! -f "/opt/mitmproxy/.mitmproxy/config.yaml" ]; then
    print_status "Creating default configuration..."
    sudo -u mitmproxy cp /opt/mitmproxy/examples/config-tor-hidden-service.yaml \
        /opt/mitmproxy/.mitmproxy/config.yaml
    sudo -u mitmproxy chmod 600 /opt/mitmproxy/.mitmproxy/config.yaml
else
    print_warning "Configuration file already exists, skipping..."
fi

# Create systemd service
print_status "Creating systemd service..."
cat > /etc/systemd/system/mitmproxy-tor.service <<'EOF'
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
EOF

# Reload systemd
systemctl daemon-reload

# Configure firewall
print_status "Configuring firewall..."
if ! command -v ufw &> /dev/null; then
    apt install -y ufw
fi

# Configure UFW
ufw --force default deny incoming
ufw --force default allow outgoing
ufw --force allow 22/tcp  # SSH
ufw --force enable

print_status "Firewall configured"

# Enable and start service
print_status "Enabling and starting mitmproxy service..."
systemctl enable mitmproxy-tor.service
systemctl start mitmproxy-tor.service

# Wait for Tor to generate .onion address
print_status "Waiting for Tor to generate .onion address (this may take 30-60 seconds)..."
sleep 60

# Display status
echo ""
echo "========================================="
echo "  Installation Complete!"
echo "========================================="
echo ""

# Check service status
if systemctl is-active --quiet mitmproxy-tor.service; then
    print_status "Service is running"
    
    # Try to get .onion address
    ONION_FILE="/opt/mitmproxy/.mitmproxy/tor/hidden_service_web/hostname"
    if [ -f "$ONION_FILE" ]; then
        ONION_ADDR=$(cat "$ONION_FILE")
        echo ""
        echo -e "${GREEN}Your .onion address:${NC} http://$ONION_ADDR"
        echo ""
        echo "Access this address using Tor Browser:"
        echo "https://www.torproject.org/download/"
    else
        print_warning ".onion address not yet generated. Wait a minute and check:"
        echo "  sudo -u mitmproxy cat $ONION_FILE"
    fi
else
    print_error "Service failed to start. Check logs:"
    echo "  sudo journalctl -u mitmproxy-tor.service -n 50"
fi

echo ""
echo "Useful commands:"
echo "  View logs:     sudo journalctl -u mitmproxy-tor.service -f"
echo "  Restart:       sudo systemctl restart mitmproxy-tor.service"
echo "  Stop:          sudo systemctl stop mitmproxy-tor.service"
echo "  Status:        sudo systemctl status mitmproxy-tor.service"
echo "  .onion addr:   sudo -u mitmproxy cat /opt/mitmproxy/.mitmproxy/tor/hidden_service_web/hostname"
echo ""
echo "For detailed documentation, see:"
echo "  /opt/mitmproxy/DEPLOY_TOR_UBUNTU.md"
echo ""
