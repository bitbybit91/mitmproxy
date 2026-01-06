# Tor Hidden Service Support for mitmproxy

This version of mitmproxy includes built-in support for running as a Tor hidden service, allowing you to access the web interface and proxy through the Tor network via a .onion address.

## Features

- **Hidden Service Web Interface**: Access mitmweb through Tor Browser using a .onion address
- **Hidden Service Proxy**: Optionally expose the proxy itself via .onion (advanced usage)
- **Automatic Tor Configuration**: Automatic torrc generation and Tor process management
- **Persistent .onion Address**: Your hidden service keys are stored and reused
- **Secure by Default**: Web interface only accessible via Tor, not exposed to the internet

## Quick Start

### Ubuntu/Debian VPS Deployment

For a complete, automated setup on Ubuntu, use the provided setup script:

```bash
# Download and run the setup script
wget https://raw.githubusercontent.com/bitbybit91/mitmproxy/master/setup-tor-ubuntu.sh
sudo bash setup-tor-ubuntu.sh
```

This will:
1. Install all dependencies (Python, Tor, build tools)
2. Set up mitmproxy with virtual environment
3. Configure Tor hidden service
4. Create systemd service for auto-start
5. Configure firewall for security

### Manual Quick Start

1. **Install Tor**:
   ```bash
   sudo apt install tor
   ```

2. **Install this version of mitmproxy**:
   ```bash
   git clone https://github.com/bitbybit91/mitmproxy.git
   cd mitmproxy
   ./dev.sh
   . venv/bin/activate
   ```

3. **Start mitmweb with Tor support**:
   ```bash
   mitmweb --set tor_enabled=true --set web_open_browser=false
   ```

4. **Get your .onion address**:
   ```bash
   cat ~/.mitmproxy/tor/hidden_service_web/hostname
   ```

5. **Access via Tor Browser**:
   - Download [Tor Browser](https://www.torproject.org/download/)
   - Navigate to your .onion address

## Configuration

### Command Line Options

Enable Tor support with command line flags:

```bash
mitmweb \
    --set tor_enabled=true \
    --set web_open_browser=false \
    --set web_host=127.0.0.1 \
    --set web_port=8081
```

Additional Tor options:

```bash
--set tor_data_dir=~/.mitmproxy/tor      # Directory for Tor data
--set tor_control_port=9051               # Tor control port
--set tor_socks_port=9050                 # Tor SOCKS port
--set tor_web_service=true                # Enable web hidden service
--set tor_proxy_service=false             # Enable proxy hidden service
```

### Configuration File

Create `~/.mitmproxy/config.yaml`:

```yaml
# Enable Tor hidden service
tor_enabled: true
tor_web_service: true
tor_proxy_service: false

# Web interface settings
web_host: 127.0.0.1
web_port: 8081
web_open_browser: false

# Proxy settings
listen_host: 127.0.0.1
listen_port: 8080
```

Then start with:

```bash
mitmweb --set confdir=~/.mitmproxy
```

See [examples/config-tor-hidden-service.yaml](examples/config-tor-hidden-service.yaml) for a complete configuration example.

## Usage Scenarios

### 1. Remote Access to mitmweb

Access mitmweb running on a remote VPS through Tor:

```bash
# On VPS
mitmweb --set tor_enabled=true --set web_open_browser=false

# Get .onion address
cat ~/.mitmproxy/tor/hidden_service_web/hostname

# From anywhere: Open Tor Browser and navigate to the .onion address
```

### 2. Anonymous Proxy Access

Make the proxy itself accessible via hidden service:

```bash
mitmweb \
    --set tor_enabled=true \
    --set tor_web_service=true \
    --set tor_proxy_service=true
```

Then configure your application to use the proxy .onion address and port 8080.

### 3. Production Deployment

For production use, deploy with systemd service:

See [DEPLOY_TOR_UBUNTU.md](DEPLOY_TOR_UBUNTU.md) for complete production deployment guide.

## Security Considerations

### Best Practices

1. **Never expose web_host to 0.0.0.0**: Always use `127.0.0.1` to prevent direct access
2. **Firewall Configuration**: Block ports 8080, 8081, 9050, 9051 from internet
3. **Keep .onion Private**: Only share with trusted parties
4. **Backup Hidden Service Keys**: Located in `~/.mitmproxy/tor/hidden_service_*/`
5. **Use Authentication**: Add proxy authentication for extra security
6. **Keep Updated**: Regularly update both Tor and mitmproxy

### Security Features

- Tor handles all encryption and anonymity
- Web interface only accessible through Tor network
- No direct internet exposure of services
- Automatic Tor process management
- Proper file permissions on Tor data directories

### Known Limitations

- .onion addresses are slow to load initially (Tor network overhead)
- Requires Tor Browser or Tor proxy to access
- Hidden service keys must be backed up to preserve .onion address

## Architecture

### How It Works

1. **Startup**: When `tor_enabled=true`, the addon starts a Tor process
2. **Configuration**: Generates a torrc file with hidden service configuration
3. **Hidden Service**: Tor creates a .onion address mapping to local web interface
4. **Access**: Users connect via Tor network to the .onion address
5. **Forwarding**: Tor forwards requests to local 127.0.0.1:8081 (web interface)

### Directory Structure

```
~/.mitmproxy/
├── config.yaml                        # Main configuration
└── tor/                               # Tor data directory
    ├── torrc                          # Generated Tor configuration
    ├── hidden_service_web/            # Web interface hidden service
    │   ├── hostname                   # Your .onion address
    │   ├── hs_ed25519_public_key      # Public key
    │   └── hs_ed25519_secret_key      # Private key (keep safe!)
    └── hidden_service_proxy/          # Proxy hidden service (if enabled)
        ├── hostname
        ├── hs_ed25519_public_key
        └── hs_ed25519_secret_key
```

### Components

- **tor_service.py**: Main addon implementing Tor integration
- **torrc**: Auto-generated Tor configuration
- **Hidden Service**: Tor's onion service functionality
- **Web Interface**: Standard mitmweb running on localhost

## Troubleshooting

### Service Won't Start

Check if Tor is installed:
```bash
which tor
tor --version
```

Install if missing:
```bash
sudo apt install tor
```

### .onion Address Not Generated

Wait 30-60 seconds after starting, then check:
```bash
cat ~/.mitmproxy/tor/hidden_service_web/hostname
```

View Tor logs:
```bash
cat ~/.mitmproxy/tor/notice.log
```

### Permission Errors

Fix permissions:
```bash
chmod 700 ~/.mitmproxy/tor
chmod 700 ~/.mitmproxy/tor/hidden_service_*
```

### Port Conflicts

Check for processes using Tor ports:
```bash
lsof -i :9050
lsof -i :9051
```

Change ports if needed:
```bash
mitmweb --set tor_control_port=9151 --set tor_socks_port=9150
```

### Can't Access .onion Address

1. Ensure you're using Tor Browser or a Tor-enabled browser
2. Check service is running: `ps aux | grep tor`
3. Verify .onion address: `cat ~/.mitmproxy/tor/hidden_service_web/hostname`
4. Check mitmweb logs for errors

## Development

### Running Tests

```bash
# Run basic syntax check
python3 -m py_compile mitmproxy/addons/tor_service.py

# Test Tor addon loading
python3 -c "from mitmproxy.addons import tor_service; print('OK')"
```

### Debugging

Enable verbose logging:
```bash
mitmweb --set tor_enabled=true -v
```

View detailed logs:
```bash
# mitmproxy logs
tail -f ~/.mitmproxy/tor/notice.log

# Systemd logs (if using service)
sudo journalctl -u mitmproxy-tor -f
```

## FAQ

**Q: Is this secure?**
A: Yes, when configured properly. The hidden service uses Tor's encryption and routing. However, keep your .onion address private and use additional authentication if needed.

**Q: Can I use my own .onion address?**
A: Yes, backup your hidden service keys from `~/.mitmproxy/tor/hidden_service_*/` and restore them to preserve your .onion address.

**Q: What happens if my VPS restarts?**
A: If you set up the systemd service (see deployment guide), mitmproxy with Tor will start automatically on boot.

**Q: Can I run multiple hidden services?**
A: Yes, use different `tor_data_dir` for each instance and different ports for web_port and listen_port.

**Q: Do I need to configure my firewall?**
A: Yes! Block ports 8080, 8081, 9050, 9051 from internet access. Only allow SSH (22).

**Q: How do I backup my .onion address?**
A: Backup the entire `~/.mitmproxy/tor/hidden_service_*` directories. The private keys in these directories determine your .onion address.

## Documentation

- [Full Deployment Guide](DEPLOY_TOR_UBUNTU.md) - Complete VPS setup instructions
- [Configuration Example](examples/config-tor-hidden-service.yaml) - Full config file example
- [mitmproxy Docs](https://docs.mitmproxy.org/) - Official mitmproxy documentation
- [Tor Project](https://www.torproject.org/) - Tor network documentation

## Contributing

Contributions are welcome! Please:

1. Test thoroughly on Ubuntu/Debian systems
2. Follow existing code style
3. Update documentation as needed
4. Consider security implications

## License

This addon is part of mitmproxy and follows the same MIT license.

## Acknowledgments

- [mitmproxy](https://mitmproxy.org/) - The original project
- [Tor Project](https://www.torproject.org/) - Anonymous communication network
