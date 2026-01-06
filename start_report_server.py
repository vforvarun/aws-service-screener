#!/usr/bin/env python3
"""
AWS Service Screener - Standalone Report Server
===============================================

This script starts a local web server to view the AWS Service Screener report.
It's designed to be included in the output.zip file for easy offline viewing.

Usage:
    python3 start_report_server.py [port]

Examples:
    python3 start_report_server.py          # Uses default port 8000
    python3 start_report_server.py 8080     # Uses port 8080

Requirements:
    - Python 3.x (built-in modules only)
    - Extract the output.zip file first
    - Run this script from the extracted directory
"""

import http.server
import socketserver
import webbrowser
import os
import sys
import time
import threading
from pathlib import Path

class ReportServerHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler to add CORS headers and better error handling"""
    
    def end_headers(self):
        # Add CORS headers to allow local file access
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def log_message(self, format, *args):
        """Override to provide cleaner logging"""
        print(f"[{time.strftime('%H:%M:%S')}] {format % args}")

def find_available_port(start_port=8000, max_attempts=10):
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socketserver.TCPServer(("", port), ReportServerHandler) as test_server:
                return port
        except OSError:
            continue
    return None

def find_main_index():
    """Find the main index.html file in the current directory structure"""
    current_dir = Path('.')
    
    # Look for directories that might contain the main report (account IDs)
    for item in current_dir.iterdir():
        if item.is_dir() and item.name.isdigit():
            index_file = item / 'index.html'
            if index_file.exists():
                return str(index_file)
    
    # Fallback: look for any index.html in current directory
    if (current_dir / 'index.html').exists():
        return 'index.html'
    
    # Look for index.html in subdirectories
    for item in current_dir.iterdir():
        if item.is_dir():
            index_file = item / 'index.html'
            if index_file.exists():
                return str(index_file)
    
    return None

def print_banner():
    """Print a nice banner"""
    print("=" * 60)
    print("🚀 AWS Service Screener - Report Server")
    print("=" * 60)

def print_instructions(port, index_path=None):
    """Print usage instructions"""
    base_url = f"http://localhost:{port}"
    
    print(f"\n✅ Report server started successfully!")
    print(f"🌐 Server running at: {base_url}")
    
    if index_path:
        full_url = f"{base_url}/{index_path}"
        print(f"📊 Main report: {full_url}")
    else:
        print(f"📁 Browse files at: {base_url}")
        print("💡 Look for index.html files in the account directories")
    
    print(f"\n📋 Instructions:")
    print(f"   • Open your web browser")
    print(f"   • Navigate to: {base_url}")
    if index_path:
        print(f"   • Or go directly to: {base_url}/{index_path}")
    print(f"   • Press Ctrl+C to stop the server")
    print("=" * 60)

def auto_open_browser(url, delay=2):
    """Auto-open browser after a delay"""
    def open_browser():
        time.sleep(delay)
        try:
            webbrowser.open(url)
            print(f"🌐 Opened {url} in your default browser")
        except Exception as e:
            print(f"⚠️  Could not auto-open browser: {e}")
            print(f"💡 Please manually open: {url}")
    
    thread = threading.Thread(target=open_browser, daemon=True)
    thread.start()

def main():
    print_banner()
    
    # Check if we're in the right directory
    if not any(Path('.').iterdir()):
        print("❌ Error: This directory appears to be empty")
        print("💡 Make sure you've extracted the output.zip file and are running this script from the extracted directory")
        sys.exit(1)
    
    # Parse command line arguments
    default_port = 8000
    if len(sys.argv) > 1:
        try:
            default_port = int(sys.argv[1])
        except ValueError:
            print(f"❌ Error: Invalid port number '{sys.argv[1]}'. Using default port {default_port}")
    
    # Find available port
    port = find_available_port(default_port)
    if not port:
        print(f"❌ Error: Could not find an available port starting from {default_port}")
        print("💡 Try specifying a different port: python3 start_report_server.py 8080")
        sys.exit(1)
    
    # Find the main index file
    index_path = find_main_index()
    
    try:
        # Create and start server
        with socketserver.TCPServer(("", port), ReportServerHandler) as httpd:
            print_instructions(port, index_path)
            
            # Auto-open browser
            if index_path:
                auto_open_browser(f"http://localhost:{port}/{index_path}")
            else:
                auto_open_browser(f"http://localhost:{port}")
            
            print(f"\n🔄 Server is running... (Press Ctrl+C to stop)")
            print("-" * 60)
            
            # Start serving
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print(f"\n\n🛑 Shutting down server...")
        print("👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()