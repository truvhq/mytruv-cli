"""Smoke test that a built binary can render a table containing non-ASCII text.

rich loads its character width tables with import_module at runtime, which a
compiled binary only has if the build bundled them. Rendering a wide character
in table mode is what exercises that path, and table mode needs a TTY.

Usage: python scripts/smoke_table.py path/to/binary
"""

import json
import os
import pty
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

PROVIDER_NAME = "Chase Bank ★ 日本"


class _LinksHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        body = json.dumps(
            [{"id": "link-1", "provider": {"name": PROVIDER_NAME}, "status": "done", "data_source": "smoke"}]
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        pass


def main() -> int:
    binary = Path(sys.argv[1]).resolve()

    server = HTTPServer(("127.0.0.1", 0), _LinksHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    with tempfile.TemporaryDirectory() as config_dir:
        Path(config_dir, "config.toml").write_text(
            f'server_url = "http://127.0.0.1:{server.server_port}"\n'
            "[tokens]\n"
            'access_token = "smoke"\n'
            'refresh_token = "smoke"\n'
            "expires_at = 9999999999\n"
        )
        controller, terminal = pty.openpty()
        process = subprocess.Popen(
            [str(binary), "links"],
            stdin=subprocess.DEVNULL,
            stdout=terminal,
            stderr=terminal,
            env={**os.environ, "MYTRUV_CONFIG_DIR": config_dir},
        )
        os.close(terminal)

        output = bytearray()
        while True:
            try:
                chunk = os.read(controller, 4096)
            except OSError:
                break
            if not chunk:
                break
            output.extend(chunk)
        os.close(controller)
        returncode = process.wait(timeout=60)

    server.shutdown()
    text = output.decode(errors="replace")
    if returncode != 0 or PROVIDER_NAME not in text:
        print("Table smoke test failed. Output:", file=sys.stderr)
        print(text, file=sys.stderr)
        return 1
    print("Table smoke test passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
