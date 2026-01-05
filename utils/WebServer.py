import http.server
import socketserver
import threading
import webbrowser
import time
import os
from utils.Tools import _info, _warn

class WebServerManager:
    def __init__(self):
        self.server = None
        self.server_thread = None
        self.port = None
        
    def find_available_port(self, start_port=8000, max_attempts=10):
        """Find an available port starting from start_port"""
        for port in range(start_port, start_port + max_attempts):
            try:
                with socketserver.TCPServer(("", port), http.server.SimpleHTTPRequestHandler) as test_server:
                    return port
            except OSError:
                continue
        return None
    
    def start_server(self, directory, auto_open=True):
        """Start a web server in the specified directory"""
        if not os.path.exists(directory):
            _warn(f"Directory {directory} does not exist")
            return False
            
        # Find available port
        self.port = self.find_available_port()
        if not self.port:
            _warn("Could not find an available port for web server")
            return False
            
        # Change to the directory
        original_dir = os.getcwd()
        
        try:
            os.chdir(directory)
            
            # Create server
            handler = http.server.SimpleHTTPRequestHandler
            self.server = socketserver.TCPServer(("", self.port), handler)
            
            # Start server in a separate thread
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            
            _info(f"Web server started on http://localhost:{self.port}")
            
            # Find the main index.html file
            index_path = self.find_main_index()
            if index_path:
                full_url = f"http://localhost:{self.port}/{index_path}"
                _info(f"Report available at: {full_url}")
                
                if auto_open:
                    # Wait a moment for server to fully start
                    time.sleep(1)
                    try:
                        webbrowser.open(full_url)
                        _info("Opening report in your default browser...")
                    except Exception as e:
                        _warn(f"Could not auto-open browser: {e}")
                        _info(f"Please manually open: {full_url}")
            else:
                _info(f"Server running at: http://localhost:{self.port}")
                
            return True
            
        except Exception as e:
            _warn(f"Failed to start web server: {e}")
            return False
        finally:
            os.chdir(original_dir)
    
    def find_main_index(self):
        """Find the main index.html file in the current directory structure"""
        # Look for directories that might contain the main report
        for item in os.listdir('.'):
            if os.path.isdir(item) and item.isdigit():
                # This looks like an account ID directory
                index_file = os.path.join(item, 'index.html')
                if os.path.exists(index_file):
                    return index_file
        
        # Fallback: look for any index.html
        if os.path.exists('index.html'):
            return 'index.html'
            
        return None
    
    def stop_server(self):
        """Stop the web server"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            _info("Web server stopped")
            
    def get_server_info(self):
        """Get server information"""
        if self.server and self.port:
            return {
                'running': True,
                'port': self.port,
                'url': f"http://localhost:{self.port}"
            }
        return {'running': False}