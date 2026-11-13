"""Serve only the local 3D study and its bundled three.js dependency."""
import argparse
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
ASSETS = {"/": ROOT / "index.html"}
for name in ("index.html", "style.css", "app.js", "scene.js", "pawn.js", "movement.js", "fixture.json"):
    ASSETS["/" + name] = ROOT / name
ASSETS["/vendor/three/three.module.js"] = ROOT.parent / "vendor" / "three" / "three.module.js"


class Preview(BaseHTTPRequestHandler):
    def do_GET(self):
        asset = ASSETS.get(urlparse(self.path).path)
        if asset is None or not asset.is_file():
            self.send_error(404, "Asset not found; generate fixture.json with make_fixture.py first")
            return
        raw = asset.read_bytes()
        content_type = "text/javascript" if asset.suffix == ".js" else mimetypes.guess_type(asset.name)[0]
        self.send_response(200)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)


def preview_server(port=8879):
    return ThreadingHTTPServer(("127.0.0.1", port), Preview)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8879)
    server = preview_server(parser.parse_args().port)
    print(f"3D pawn study: http://127.0.0.1:{server.server_address[1]}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
