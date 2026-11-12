"""Local connected-board preview. Delegates every game request to the existing server."""
import argparse
import mimetypes
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / "src"))
from traveler_quartet.match.server import make_server

ASSETS = {"/": ROOT / "index.html", "/index.html": ROOT / "index.html"}
for name in ("board.css", "model.js", "client.js", "render.js", "app.js"):
    ASSETS["/" + name] = ROOT / name
for name in ("merchant.svg", "village.svg"):
    ASSETS["/" + name] = ROOT.parent / "front-purchase" / name

def preview_server(port=8878):
    server = make_server(port=port)
    base = server.RequestHandlerClass
    class Preview(base):
        def do_GET(self):
            asset = ASSETS.get(urlparse(self.path).path)
            if asset is None:
                return super().do_GET()
            raw = asset.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(asset.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)
    server.RequestHandlerClass = Preview
    return server

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8878)
    args = parser.parse_args()
    server = preview_server(args.port)
    print("Connected board: http://127.0.0.1:"+str(server.server_address[1]), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
