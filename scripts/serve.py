"""Preview the built site on this machine, with caching off.

    python scripts/serve.py [port]       then open http://127.0.0.1:8770/

Opening docs/index.html straight from the folder breaks photos and fonts in some
browsers, so preview through this instead.
"""
import functools
import http.server
import sys
from pathlib import Path


class NoStore(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):
        pass


class Server(http.server.ThreadingHTTPServer):
    request_queue_size = 128   # Windows refuses a browser's parallel burst at the default 5
    daemon_threads = True


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8770
    docs = Path(__file__).resolve().parent.parent / "docs"
    Server(("127.0.0.1", port), functools.partial(NoStore, directory=str(docs))).serve_forever()
