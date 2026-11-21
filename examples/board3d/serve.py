"""Serve the local 3D board; delegate game transport to the existing arbiter server."""
import argparse
import json
import mimetypes
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
mimetypes.add_type("image/webp", ".webp")  # unknown to some Windows registries
sys.path.insert(0, str(ROOT.parents[1] / "src"))
from traveler_quartet.match.server import make_server

ASSETS = {"/": ROOT / "index.html"}
for name in ("index.html", "style.css", "app.js", "scene.js", "pawn.js", "movement.js", "layout.js", "client.js",
             "camera.js", "play.js", "trade.js", "art.js", "fixture.json"):
    ASSETS["/" + name] = ROOT / name
for name in ("gallery.html", "gallery.css", "gallery.js", "merchants.js", "MANIFEST.md"):
    ASSETS["/art/" + name] = ROOT / "art" / name
ASSETS["/vendor/three/three.module.js"] = ROOT.parent / "vendor" / "three" / "three.module.js"
# The illustrations (D57): the WebP exports LISTED in web.json and the three lists -- never a PNG master.
ILLUSTRATIONS = ROOT / "art" / "illustrations"
for name in ("catalog.json", "web.json", "banner-crops.json"):
    ASSETS["/art/illustrations/" + name] = ILLUSTRATIONS / name
if (ILLUSTRATIONS / "web.json").is_file():
    for exported in json.loads((ILLUSTRATIONS / "web.json").read_text(encoding="utf-8"))["assets"]:
        ASSETS["/art/illustrations/" + exported["file"]] = ILLUSTRATIONS / exported["file"]


def preview_server(port=8879):
    server = make_server(port=port)
    base = server.RequestHandlerClass

    class Preview(base):
        def do_GET(self):
            asset = ASSETS.get(urlparse(self.path).path)
            if asset is None:
                return super().do_GET()
            if not asset.is_file():
                self.send_error(404, "Preview asset not found")
                return
            raw = asset.read_bytes()
            content_type = "text/javascript" if asset.suffix == ".js" else mimetypes.guess_type(asset.name)[0]
            self.send_response(200)
            self.send_header("Content-Type", content_type or "application/octet-stream")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)

    server.RequestHandlerClass = Preview
    return server


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8879)
    server = preview_server(parser.parse_args().port)
    print(f"3D public board: http://127.0.0.1:{server.server_address[1]}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
