#!/usr/bin/env python3
"""Simple HTTP server with configurable logging."""

import http.server
import socketserver
import sys

# Toggle this to enable/disable request logging
LOG_REQUESTS = False

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        if LOG_REQUESTS:
            super().log_message(format, *args)


with socketserver.TCPServer(('', PORT), Handler) as httpd:
    print(f"Serving at http://localhost:{PORT}")
    httpd.serve_forever()
