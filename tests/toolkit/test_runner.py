"""capture/runner.py: readiness polling and image difference (FR-002a, FR-027)."""
import http.server
import json
import sys
import threading
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "guide" / "toolkit" / "capture"))
import runner  # noqa: E402


class _Handler(http.server.BaseHTTPRequestHandler):
    statuses: list[int] = []

    def do_GET(self):  # noqa: N802
        status = self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
        self.send_response(status)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        pass


@pytest.fixture
def server():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv
    srv.shutdown()


def url(srv) -> str:
    return f"http://127.0.0.1:{srv.server_address[1]}/health"


def test_ready_immediately(server):
    _Handler.statuses = [200]
    assert runner.ready(url(server), timeout=5, interval=0.05) == (True, "status 200")


def test_ready_after_errors(server):
    _Handler.statuses = [500, 503, 302]
    ok, detail = runner.ready(url(server), timeout=5, interval=0.05)
    assert ok and detail == "status 302"


def test_ready_timeout_reports_last_status(server):
    _Handler.statuses = [404]
    ok, detail = runner.ready(url(server), timeout=0.3, interval=0.05)
    assert not ok and detail == "status 404"


def test_ready_connection_error():
    ok, detail = runner.ready("http://127.0.0.1:9/", timeout=0.3, interval=0.05)
    assert not ok and detail.startswith("connection error")


def test_ready_cli_exit_codes(server, capsys):
    _Handler.statuses = [200]
    assert runner.main(["ready", "--url", url(server), "--timeout", "2"]) == 0
    _Handler.statuses = [500]
    assert runner.main(["ready", "--url", url(server), "--timeout", "0.2"]) == 1
    assert "status 500" in capsys.readouterr().out


def png(path: Path, size=(10, 10), color=(255, 255, 255), pixels=None) -> Path:
    img = Image.new("RGB", size, color)
    for xy, value in (pixels or {}).items():
        img.putpixel(xy, value)
    img.save(path)
    return path


def test_diff_identical(tmp_path):
    a = png(tmp_path / "a.png")
    b = png(tmp_path / "b.png")
    assert runner.image_diff(a, b, 16) == 0.0


def test_diff_below_tolerance(tmp_path):
    a = png(tmp_path / "a.png")
    b = png(tmp_path / "b.png", pixels={(0, 0): (250, 240, 255), (1, 1): (239, 255, 255)})
    assert runner.image_diff(a, b, 16) == 0.0


def test_diff_above_tolerance(tmp_path):
    a = png(tmp_path / "a.png")
    b = png(tmp_path / "b.png", pixels={(0, 0): (200, 255, 255), (5, 5): (0, 0, 0)})
    assert runner.image_diff(a, b, 16) == 2.0


def test_diff_size_mismatch(tmp_path, capsys):
    a = png(tmp_path / "a.png")
    b = png(tmp_path / "b.png", size=(10, 11))
    assert runner.image_diff(a, b, 16) == 100.0
    assert runner.main(["diff", str(a), str(b), "--tolerance", "16"]) == 0
    assert json.loads(capsys.readouterr().out) == {"diff": 100.0}
