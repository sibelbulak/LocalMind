import json
import errno
import re
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from socketserver import TCPServer
from urllib.parse import unquote, urlparse
from .config import DOCUMENTS_PATH, STATIC_PATH


class AppHandler(SimpleHTTPRequestHandler):
    service = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_PATH), **kwargs)

    def send_json(self, value, status=200):
        body = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self):
        if urlparse(self.path).path == "/api/status":
            return self.send_json({**self.service.db.stats(), "backend": self.service.backend.name, "ready": True, "version": "1.1.0"})
        return super().do_GET()

    def do_POST(self):
        route = urlparse(self.path).path
        if route == "/api/upload":
            return self.handle_upload()
        if route != "/api/ask":
            return self.send_json({"error": "Bulunamadı"}, 404)
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
            return self.send_json(self.service.ask(str(payload.get("question", ""))))
        except (ValueError, json.JSONDecodeError) as exc:
            return self.send_json({"error": str(exc)}, 400)
        except Exception as exc:
            return self.send_json({"error": f"İşlem başarısız: {exc}"}, 500)

    def handle_upload(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0:
                raise ValueError("Dosya boş.")
            if length > 10 * 1024 * 1024:
                raise ValueError("Dosya boyutu en fazla 10 MB olabilir.")
            original = unquote(self.headers.get("X-Filename", ""))
            filename = re.sub(r"[^a-zA-Z0-9çğıöşüÇĞİÖŞÜ._ -]", "_", original).strip(". ")
            if not filename or "." not in filename:
                raise ValueError("Geçerli bir dosya adı gerekli.")
            if not filename.lower().endswith((".txt", ".md", ".pdf")):
                raise ValueError("Yalnızca TXT, MD ve PDF dosyaları destekleniyor.")
            DOCUMENTS_PATH.mkdir(parents=True, exist_ok=True)
            target = DOCUMENTS_PATH / filename
            target.write_bytes(self.rfile.read(length))
            try:
                indexed = self.service.ingest_path(target)
            except Exception:
                target.unlink(missing_ok=True)
                raise
            return self.send_json({"message": f"{filename} yüklendi ve indekslendi.", **indexed, **self.service.db.stats()})
        except (ValueError, UnicodeError, RuntimeError) as exc:
            return self.send_json({"error": str(exc)}, 400)
        except Exception as exc:
            return self.send_json({"error": f"Yükleme başarısız: {exc}"}, 500)

    def log_message(self, fmt, *args):
        print(f"[web] {fmt % args}")


class LocalHTTPServer(ThreadingHTTPServer):
    """Avoid HTTPServer's reverse-DNS lookup, which can stall offline."""
    allow_reuse_address = True

    def server_bind(self):
        TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = host
        self.server_port = port


def serve(service, host="127.0.0.1", port=8000):
    AppHandler.service = service
    requested_port = port
    for candidate in range(requested_port, requested_port + 20):
        try:
            server = LocalHTTPServer((host, candidate), AppHandler)
            port = candidate
            break
        except OSError as exc:
            if exc.errno != errno.EADDRINUSE:
                raise
    else:
        raise OSError(f"{requested_port}-{requested_port + 19} aralığında boş port bulunamadı.")
    if port != requested_port:
        print(f"Port {requested_port} kullanımda; otomatik olarak {port} seçildi.")
    print(f"LocalMind hazır: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSunucu durduruldu.")
    finally:
        server.server_close()
