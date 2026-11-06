"""The offline page is a packaged resource, served by the real local HTTP server."""

import re
import threading
import urllib.request
from importlib.resources import files

import pytest

from traveler_quartet.match.server import make_server


@pytest.fixture
def page():
    server = make_server(port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{server.server_address[1]}/") as reply:
            yield reply.status, reply.headers, reply.read()
    finally:
        server.shutdown()
        server.server_close()


def test_root_serves_an_html_page(page):
    status, headers, body = page
    assert status == 200 and headers.get_content_type() == "text/html"
    assert int(headers["Content-Length"]) == len(body)
    assert "Traveler Quartet" in body.decode("utf-8")


def test_served_page_is_the_packaged_resource(page):
    resource = files("traveler_quartet").joinpath("web/index.html")
    assert resource.is_file()
    assert page[2] == resource.read_bytes()


def test_page_is_self_contained_and_offline(page):
    text = page[2].decode("utf-8")
    assert not re.search(r"https?://|(?:src|href)\s*=\s*['\"]//", text)
    assert not re.search(r"<(?:script|link|img)[^>]+(?:src|href)\s*=\s*['\"](?!data:)", text)


def test_page_only_fetches_the_four_game_routes(page):
    text = page[2].decode("utf-8")
    paths = re.findall(r"fetch\(([`'\"])(.*?)\1", text)
    assert {path for _, path in paths} == {
        "/games", "/games/${game}/view", "/games/${game}/act", "/games/${game}/events?since=${cursor}",
    }
    assert text.count("fetch(") == len(paths)


def test_view_and_messages_are_displayed_as_text_not_markup(page):
    text = page[2].decode("utf-8")
    assert '<pre id="state"' in text
    assert "textContent" in text and "innerHTML" not in text
    assert "Authorization" in text and "Bearer" in text
