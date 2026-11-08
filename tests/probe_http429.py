"""Local HTTP integration probe: intentionally exits 1, never creates leads."""
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import collect_leads


class RateLimited(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(429)
        self.send_header('Retry-After', '60')
        self.end_headers()
        self.wfile.write(b'Too Many Requests')

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    server = ThreadingHTTPServer(('127.0.0.1', 0), RateLimited)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    collect_leads.SOURCES = [{'name': 'Local HTTP 429 probe',
                             'url': f'http://127.0.0.1:{server.server_port}/feed'}]
    try:
        result = collect_leads.main()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    sys.exit(result)
