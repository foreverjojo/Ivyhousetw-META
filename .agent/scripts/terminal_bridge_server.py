#!/usr/bin/env python3
"""
Terminal Bridge Server - Standalone HTTP server for terminal monitoring
Provides /wait and /capture endpoints for Codex CLI automation
Replaces VS Code extension functionality when extension activation fails
"""

import http.server
import json
import subprocess
import time
import os
import sys
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, parse_qs

class TerminalBridgeHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for terminal bridge operations"""
    
    # Class variables shared across all requests
    git_status_cache: Dict[str, Any] = {}
    cache_lock = threading.Lock()
    
    def log_message(self, format, *args):
        """Override to add timestamp to logs"""
        sys.stderr.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {format % args}\n")
    
    def authenticate(self) -> bool:
        """Verify Bearer token authentication"""
        auth_header = self.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return False
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        expected_token = getattr(self.server, 'token', '')
        
        return token == expected_token
    
    def send_json_response(self, status_code: int, data: dict):
        """Send JSON response with proper headers"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def get_git_status(self) -> Dict[str, Any]:
        """Get current git status (staged + unstaged changes)"""
        try:
            # Run git status --short
            workspace_root = getattr(self.server, 'workspace_root', os.getcwd())
            result = subprocess.run(
                ['git', 'status', '--short'],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=workspace_root
            )
            
            if result.returncode == 0:
                changes = [line for line in result.stdout.strip().split('\n') if line]
                return {
                    'timestamp': time.time(),
                    'changes': changes,
                    'count': len(changes)
                }
            else:
                return {'timestamp': time.time(), 'changes': [], 'count': 0, 'error': result.stderr}
        except Exception as e:
            return {'timestamp': time.time(), 'changes': [], 'count': 0, 'error': str(e)}
    
    def wait_for_completion(self, timeout_ms: int, check_interval_ms: int) -> Dict[str, Any]:
        """
        Wait for git status to stabilize (no changes for check_interval)
        Returns completion status and elapsed time
        """
        start_time = time.time()
        timeout_sec = timeout_ms / 1000
        check_interval_sec = check_interval_ms / 1000
        
        last_status = self.get_git_status()
        last_change_time = start_time
        
        while True:
            elapsed = time.time() - start_time
            
            # Check timeout
            if elapsed * 1000 >= timeout_ms:
                return {
                    'ok': False,
                    'completed': False,
                    'elapsed': int(elapsed * 1000),
                    'reason': 'timeout',
                    'lastStatus': last_status
                }
            
            # Wait for check interval
            time.sleep(check_interval_sec)
            
            # Get current status
            current_status = self.get_git_status()
            
            # Check if status changed
            if current_status['count'] != last_status['count'] or \
               set(current_status['changes']) != set(last_status['changes']):
                # Status changed - reset timer
                last_change_time = time.time()
                last_status = current_status
                continue
            
            # Check if stable for check_interval duration
            stability_duration = time.time() - last_change_time
            if stability_duration >= check_interval_sec:
                # Stable for at least one check interval - consider complete
                return {
                    'ok': True,
                    'completed': True,
                    'elapsed': int(elapsed * 1000),
                    'detectedChanges': last_status['count'] > 0,
                    'finalStatus': last_status
                }
    
    def do_GET(self):
        """Handle GET requests"""
        parsed = urlparse(self.path)
        path = parsed.path
        
        # Health check
        if path == '/health':
            self.send_json_response(200, {'ok': True, 'status': 'running', 'version': '0.1.0'})
            return
        
        # Capture endpoint (simplified - returns git status instead of terminal output)
        if path == '/capture':
            if not self.authenticate():
                self.send_json_response(401, {'ok': False, 'error': 'Unauthorized'})
                return
            
            # Get git status as "captured output"
            status = self.get_git_status()
            
            self.send_json_response(200, {
                'ok': True,
                'lines': status['changes'],
                'totalLines': status['count'],
                'timestamp': status['timestamp']
            })
            return
        
        self.send_json_response(404, {'ok': False, 'error': 'Not found'})
    
    def do_POST(self):
        """Handle POST requests"""
        parsed = urlparse(self.path)
        path = parsed.path
        
        # Wait endpoint
        if path == '/wait':
            if not self.authenticate():
                self.send_json_response(401, {'ok': False, 'error': 'Unauthorized'})
                return
            
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            
            try:
                params = json.loads(body) if body else {}
            except json.JSONDecodeError:
                self.send_json_response(400, {'ok': False, 'error': 'Invalid JSON'})
                return
            
            # Get parameters with defaults
            timeout_ms = params.get('timeout', 300000)  # 5 minutes default
            check_interval_ms = params.get('checkInterval', 2000)  # 2 seconds default
            
            # Execute wait logic
            result = self.wait_for_completion(timeout_ms, check_interval_ms)
            
            if result.get('ok', False):
                self.send_json_response(200, result)
            else:
                self.send_json_response(408, result)  # Request Timeout
            return
        
        self.send_json_response(404, {'ok': False, 'error': 'Not found'})
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
        self.end_headers()


class TerminalBridgeServer(http.server.HTTPServer):
    """Custom HTTP server with workspace and token support"""
    
    def __init__(self, server_address, handler_class, workspace_root: str, token: str):
        super().__init__(server_address, handler_class)
        self.workspace_root = workspace_root
        self.token = token


def load_or_generate_token(state_dir: Path) -> str:
    """Load existing token or generate new one"""
    token_file = state_dir / 'terminal_bridge_token'
    
    if token_file.exists():
        token = token_file.read_text().strip()
        if token:
            print(f"✓ Loaded existing token from {token_file}")
            return token
    
    # Generate new token
    import secrets
    token = secrets.token_urlsafe(32)
    
    # Ensure state directory exists
    state_dir.mkdir(parents=True, exist_ok=True)
    
    # Write token
    token_file.write_text(token)
    token_file.chmod(0o600)  # Read/write for owner only
    
    print(f"✓ Generated new token: {token_file}")
    return token


def write_info_file(state_dir: Path, port: int, token: str):
    """Write server info to JSON file for client scripts"""
    info_file = state_dir / 'terminal_bridge_info.json'
    
    info = {
        'port': port,
        'host': '127.0.0.1',
        'endpoints': {
            '/health': 'GET - Health check',
            '/capture': 'GET - Get git status changes',
            '/wait': 'POST - Wait for git status to stabilize'
        },
        'token_file': str(state_dir / 'terminal_bridge_token'),
        'version': '0.1.0-standalone'
    }
    
    info_file.write_text(json.dumps(info, indent=2))
    print(f"✓ Server info written to {info_file}")


def main():
    """Main entry point"""
    # Configuration
    port = int(os.getenv('TERMINAL_BRIDGE_PORT', '38765'))
    host = '127.0.0.1'
    
    # Determine workspace root
    workspace_root = os.getenv('WORKSPACE_ROOT', os.getcwd())
    
    # Ensure we're in a git repository
    git_dir = Path(workspace_root) / '.git'
    if not git_dir.exists():
        print(f"❌ Error: {workspace_root} is not a git repository", file=sys.stderr)
        sys.exit(1)
    
    # State directory
    state_dir = Path(workspace_root) / '.agent' / 'state'
    
    # Load or generate authentication token
    token = load_or_generate_token(state_dir)
    
    # Write info file
    write_info_file(state_dir, port, token)
    
    # Create and start server
    server = TerminalBridgeServer((host, port), TerminalBridgeHandler, workspace_root, token)
    
    print(f"")
    print(f"🚀 Terminal Bridge Server started")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Workspace: {workspace_root}")
    print(f"   Token file: {state_dir / 'terminal_bridge_token'}")
    print(f"")
    print(f"📡 Available endpoints:")
    print(f"   GET  /health  - Health check")
    print(f"   GET  /capture - Get git status changes")
    print(f"   POST /wait    - Wait for git status to stabilize")
    print(f"")
    print(f"Press Ctrl+C to stop")
    print(f"")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n⏹️  Server stopped")
        server.shutdown()
        sys.exit(0)


if __name__ == '__main__':
    main()
