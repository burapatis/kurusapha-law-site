#!/usr/bin/env python3
"""เปิดเว็บไซต์พร้อมสิทธิ์อ่านไฟล์ต้นฉบับจากคลังกฎหมายในเครื่อง

เซิร์ฟเวอร์ผูกกับ 127.0.0.1 เท่านั้น และเปิดได้เฉพาะ id ที่อยู่ใน
data/catalog.json จึงไม่เปิดให้ระบุพาธไฟล์ตามอำเภอใจ
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlparse


SITE = Path(__file__).resolve().parents[1]
DOCUMENTS = SITE.parent.parent
ROOTS = {
    "กฎหมายคุรุสภา": SITE.parent.resolve(),
    "กฎหมายหลัก": (DOCUMENTS / "กฎหมายหลัก").resolve(),
    "กฎหมายหลักการศึกษา": (DOCUMENTS / "กฎหมายหลักการศึกษา").resolve(),
}
ID_PATTERN = re.compile(r"^doc-[0-9a-f]{8}$")


def load_catalog() -> dict[str, dict]:
    data = json.loads((SITE / "data" / "catalog.json").read_text("utf-8"))
    return {item["id"]: item for item in data.get("items", [])}


def resolve_source(item: dict) -> Path | None:
    """คืนไฟล์แรกที่มีอยู่จริง โดยป้องกัน path traversal ทุกกรณี"""
    sources = sorted(item.get("sources", []), key=lambda source: source.get("ext") == "txt")
    for source in sources:
        root = ROOTS.get(source.get("corpus"))
        if not root:
            continue
        candidate = (root / source.get("path", "")).resolve()
        if not candidate.is_relative_to(root) or not candidate.is_file():
            continue
        return candidate
    return None


class ArchiveHandler(SimpleHTTPRequestHandler):
    server_version = "KurusaphaLocalArchive/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE), **kwargs)

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    def do_GET(self) -> None:  # noqa: N802 - ชื่อตาม BaseHTTPRequestHandler
        path = unquote(urlparse(self.path).path)
        if path == "/__local_source__/__health__":
            payload = json.dumps({"available": True, "mode": "local-archive"}, ensure_ascii=False).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)
            return

        if path.startswith("/__local_source__/"):
            item_id = path.rsplit("/", 1)[-1]
            if not ID_PATTERN.fullmatch(item_id):
                self.send_error(HTTPStatus.BAD_REQUEST, "Invalid document id")
                return
            item = load_catalog().get(item_id)
            source = resolve_source(item) if item else None
            if not source:
                self.send_error(HTTPStatus.NOT_FOUND, "Source file not found")
                return
            content_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(source.stat().st_size))
            self.send_header("Content-Disposition", f"inline; filename*=UTF-8''{quote(source.name)}")
            self.send_header("Cache-Control", "private, no-store")
            self.end_headers()
            with source.open("rb") as stream:
                self.copyfile(stream, self.wfile)
            return

        super().do_GET()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8080, help="พอร์ตภายในเครื่อง (ค่าเริ่มต้น 8080)")
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), ArchiveHandler)
    print(f"เปิดเว็บไซต์ภายในเครื่องที่ http://127.0.0.1:{args.port}/")
    print("กด Ctrl+C เพื่อปิด — เซิร์ฟเวอร์รับการเชื่อมต่อจากเครื่องนี้เท่านั้น")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nปิดเซิร์ฟเวอร์แล้ว")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
