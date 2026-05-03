#!/usr/bin/env python3
"""轻量 HTTP 服务：静态文件 + /api/refresh 刷新数据。"""

import json
import os
import subprocess
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

PORT = int(os.environ.get("PORT", 8765))
DIR = Path(__file__).parent
GENERATE = DIR / "generate.py"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIR), **kwargs)

    def do_GET(self):
        if self.path == "/api/refresh":
            self._handle_refresh()
        else:
            super().do_GET()

    def _handle_refresh(self):
        try:
            result = subprocess.run(
                [sys.executable, str(GENERATE)],
                capture_output=True, text=True, timeout=30,
            )
            success = result.returncode == 0
            # 读取生成的数据摘要
            data_file = DIR / "data.json"
            summary = ""
            if data_file.exists():
                data = json.loads(data_file.read_text())
                summary = f"{data['project_count']} projects scanned"
            body = json.dumps({
                "success": success,
                "message": summary if success else result.stderr.strip(),
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            body = json.dumps({"success": False, "message": str(e)}).encode()
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, format, *args):
        # 静默常规日志，只报错
        if "200" not in str(args):
            super().log_message(format, *args)


def main():
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Project Browser serving on http://0.0.0.0:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
