#!/usr/bin/env python3
"""
Simple HTTP server with logging disabled
"""
import http.server
import socketserver
import sys
import os

class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler that doesn't log requests"""
    
    def log_message(self, format, *args):
        """Override to suppress logging"""
        pass

def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    bind_address = sys.argv[2] if len(sys.argv) > 2 else '127.0.0.1'
    
    # Change to web directory
    web_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(web_dir)
    
    with socketserver.TCPServer((bind_address, port), QuietHTTPRequestHandler) as httpd:
        print(f"Serving HTTP on {bind_address} port {port} (http://{bind_address}:{port}/) ...")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received, exiting.")
            sys.exit(0)

if __name__ == '__main__':
    main()
