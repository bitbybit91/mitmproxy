"""
Tor Hidden Service support for mitmproxy.

This addon enables mitmproxy to run as a Tor hidden service,
making both the web interface and proxy accessible via .onion addresses.
"""
import os
import subprocess
import time
import logging
from pathlib import Path
from typing import Optional

from mitmproxy import ctx
from mitmproxy import exceptions


logger = logging.getLogger(__name__)


class TorService:
    """
    Addon to configure and run mitmproxy as a Tor hidden service.
    """
    
    def __init__(self):
        self.tor_process: Optional[subprocess.Popen] = None
        self.onion_address: Optional[str] = None
        self.tor_data_dir: Optional[Path] = None
        
    def load(self, loader):
        loader.add_option(
            "tor_enabled", bool, False,
            "Enable Tor hidden service support."
        )
        loader.add_option(
            "tor_data_dir", str, "",
            "Directory for Tor data and hidden service keys. "
            "Defaults to ~/.mitmproxy/tor"
        )
        loader.add_option(
            "tor_control_port", int, 9051,
            "Tor control port."
        )
        loader.add_option(
            "tor_socks_port", int, 9050,
            "Tor SOCKS proxy port."
        )
        loader.add_option(
            "tor_web_service", bool, True,
            "Expose web interface as hidden service."
        )
        loader.add_option(
            "tor_proxy_service", bool, False,
            "Expose proxy as hidden service (advanced usage)."
        )
        
    def running(self):
        """Called when the proxy is completely started."""
        if not ctx.options.tor_enabled:
            return
            
        try:
            self._setup_tor()
            self._start_tor()
            self._wait_for_onion_address()
            self._log_status()
        except Exception as e:
            ctx.log.error(f"Failed to start Tor hidden service: {e}")
            raise exceptions.OptionsError(f"Tor setup failed: {e}")
    
    def done(self):
        """Called when the addon shuts down."""
        if self.tor_process:
            ctx.log.info("Stopping Tor service...")
            self.tor_process.terminate()
            try:
                self.tor_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.tor_process.kill()
                self.tor_process.wait()
            ctx.log.info("Tor service stopped")
    
    def _setup_tor(self):
        """Setup Tor directories and configuration."""
        # Determine data directory
        if ctx.options.tor_data_dir:
            self.tor_data_dir = Path(ctx.options.tor_data_dir).expanduser()
        else:
            confdir = Path(ctx.options.confdir).expanduser()
            self.tor_data_dir = confdir / "tor"
        
        # Create directories
        self.tor_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create hidden service directories
        if ctx.options.tor_web_service:
            web_hs_dir = self.tor_data_dir / "hidden_service_web"
            web_hs_dir.mkdir(exist_ok=True)
            os.chmod(web_hs_dir, 0o700)
        
        if ctx.options.tor_proxy_service:
            proxy_hs_dir = self.tor_data_dir / "hidden_service_proxy"
            proxy_hs_dir.mkdir(exist_ok=True)
            os.chmod(proxy_hs_dir, 0o700)
    
    def _generate_torrc(self) -> Path:
        """Generate Tor configuration file."""
        torrc_path = self.tor_data_dir / "torrc"
        
        config_lines = [
            "# Tor configuration for mitmproxy",
            f"DataDirectory {self.tor_data_dir}",
            f"ControlPort {ctx.options.tor_control_port}",
            f"SocksPort {ctx.options.tor_socks_port}",
            "",
        ]
        
        # Web interface hidden service
        if ctx.options.tor_web_service:
            web_hs_dir = self.tor_data_dir / "hidden_service_web"
            web_port = getattr(ctx.options, 'web_port', 8081)
            web_host = getattr(ctx.options, 'web_host', '127.0.0.1')
            config_lines.extend([
                "# Hidden service for web interface",
                f"HiddenServiceDir {web_hs_dir}",
                f"HiddenServicePort 80 {web_host}:{web_port}",
                "",
            ])
        
        # Proxy hidden service
        if ctx.options.tor_proxy_service:
            proxy_hs_dir = self.tor_data_dir / "hidden_service_proxy"
            listen_port = ctx.options.listen_port
            listen_host = ctx.options.listen_host or "127.0.0.1"
            config_lines.extend([
                "# Hidden service for proxy",
                f"HiddenServiceDir {proxy_hs_dir}",
                f"HiddenServicePort 8080 {listen_host}:{listen_port}",
                "",
            ])
        
        with open(torrc_path, 'w') as f:
            f.write('\n'.join(config_lines))
        
        os.chmod(torrc_path, 0o600)
        return torrc_path
    
    def _start_tor(self):
        """Start Tor process with generated configuration."""
        # Check if Tor is installed
        tor_binary = self._find_tor_binary()
        if not tor_binary:
            raise exceptions.OptionsError(
                "Tor is not installed. Please install Tor: sudo apt install tor"
            )
        
        torrc_path = self._generate_torrc()
        
        ctx.log.info(f"Starting Tor with config: {torrc_path}")
        
        try:
            self.tor_process = subprocess.Popen(
                [tor_binary, "-f", str(torrc_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        except Exception as e:
            raise exceptions.OptionsError(f"Failed to start Tor: {e}")
        
        # Give Tor a moment to start
        time.sleep(2)
        
        # Check if process is still running
        if self.tor_process.poll() is not None:
            stderr = self.tor_process.stderr.read() if self.tor_process.stderr else ""
            raise exceptions.OptionsError(
                f"Tor process exited unexpectedly. Error: {stderr}"
            )
    
    def _find_tor_binary(self) -> Optional[str]:
        """Find Tor binary in system PATH."""
        tor_locations = [
            "/usr/bin/tor",
            "/usr/sbin/tor",
            "/usr/local/bin/tor",
        ]
        
        for location in tor_locations:
            if os.path.isfile(location) and os.access(location, os.X_OK):
                return location
        
        # Try using 'which'
        try:
            result = subprocess.run(
                ["which", "tor"],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass
        
        return None
    
    def _wait_for_onion_address(self, timeout: int = 30):
        """Wait for Tor to generate onion address."""
        if not ctx.options.tor_web_service:
            return
        
        hostname_file = self.tor_data_dir / "hidden_service_web" / "hostname"
        
        ctx.log.info("Waiting for Tor to generate .onion address...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if hostname_file.exists():
                try:
                    with open(hostname_file, 'r') as f:
                        self.onion_address = f.read().strip()
                    return
                except Exception as e:
                    ctx.log.warn(f"Error reading hostname file: {e}")
            
            time.sleep(1)
        
        raise exceptions.OptionsError(
            "Timeout waiting for Tor to generate .onion address"
        )
    
    def _log_status(self):
        """Log the status of Tor hidden services."""
        ctx.log.info("=" * 60)
        ctx.log.info("Tor Hidden Service started successfully!")
        ctx.log.info("=" * 60)
        
        if ctx.options.tor_web_service and self.onion_address:
            ctx.log.info(f"Web interface accessible at: http://{self.onion_address}")
            web_host = getattr(ctx.options, 'web_host', '127.0.0.1')
            web_port = getattr(ctx.options, 'web_port', 8081)
            ctx.log.info(f"Local web interface: http://{web_host}:{web_port}")
        
        if ctx.options.tor_proxy_service:
            proxy_hostname_file = self.tor_data_dir / "hidden_service_proxy" / "hostname"
            if proxy_hostname_file.exists():
                with open(proxy_hostname_file, 'r') as f:
                    proxy_onion = f.read().strip()
                ctx.log.info(f"Proxy accessible at: {proxy_onion}:8080")
        
        ctx.log.info("=" * 60)


addons = [TorService()]
