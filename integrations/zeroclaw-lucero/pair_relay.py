#!/usr/bin/env python3
"""Relay ZeroClaw WhatsApp QR / pair-code into Lucero Channels dashboard.

Railway web logs mangle ASCII QR codes. This process:
1) Runs ZeroClaw
2) Captures terminal QR art or raw payload / pair code
3) POSTs a clean PNG (or pair code) to Lucero so the client can scan
   from https://lucero-zeta.vercel.app/dashboard/channels
"""

from __future__ import annotations

import base64
import io
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from typing import List, Optional

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None  # type: ignore


API_BASE = os.environ.get(
    "LUCERO_API_BASE", "https://lucero-api-production.up.railway.app"
).rstrip("/")
API_KEY = os.environ.get("LUCERO_CHANNEL_API_KEY", "").strip()
POST_URL = f"{API_BASE}/channels/pairing"

QR_START = re.compile(r"WhatsApp Web QR code", re.I)
QR_PAYLOAD = re.compile(r"WhatsApp Web QR payload:\s*(.+)$", re.I)
PAIR_CODE = re.compile(r"(?:^|\b)pair code:\s*([A-Za-z0-9]{8})\b", re.I)
CONNECTED = re.compile(r"connected successfully|whatsapp.*linked|Logged in", re.I)

# Module size in pixels when painting terminal block characters.
MODULE = 10


def _post(payload: dict) -> None:
    if not API_KEY:
        print("pair_relay: LUCERO_CHANNEL_API_KEY missing; skip publish", flush=True)
        return
    data = __import__("json").dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        POST_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            print(f"pair_relay: published pairing -> {resp.status}", flush=True)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"pair_relay: publish HTTP {exc.code}: {body}", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"pair_relay: publish failed: {exc}", flush=True)


def _char_cells(ch: str) -> List[List[int]]:
    """Return 2x2 black(1)/white(0) cells for common QR unicode blocks."""
    # Dense1x2 / half-block style used by many terminal QR renderers.
    mapping = {
        " ": [[0, 0], [0, 0]],
        "█": [[1, 1], [1, 1]],
        "▀": [[1, 1], [0, 0]],
        "▄": [[0, 0], [1, 1]],
        "▌": [[1, 0], [1, 0]],
        "▐": [[0, 1], [0, 1]],
        "▖": [[0, 0], [1, 0]],
        "▗": [[0, 0], [0, 1]],
        "▘": [[1, 0], [0, 0]],
        "▝": [[0, 1], [0, 0]],
        "▙": [[1, 0], [1, 1]],
        "▛": [[1, 1], [1, 0]],
        "▜": [[1, 1], [0, 1]],
        "▟": [[0, 1], [1, 1]],
        "▞": [[0, 1], [1, 0]],
        "▚": [[1, 0], [0, 1]],
        "■": [[1, 1], [1, 1]],
        "□": [[0, 0], [0, 0]],
        "▪": [[1, 1], [1, 1]],
        "▫": [[0, 0], [0, 0]],
        "●": [[1, 1], [1, 1]],
        "○": [[0, 0], [0, 0]],
    }
    if ch in mapping:
        return mapping[ch]
    # Fallback: treat unknown non-space as black.
    return [[1, 1], [1, 1]] if ch.strip() else [[0, 0], [0, 0]]


def ascii_qr_to_png_b64(lines: List[str]) -> Optional[str]:
    if Image is None:
        print("pair_relay: Pillow missing; cannot render QR PNG", flush=True)
        return None
    rows = [ln.rstrip("\n") for ln in lines if ln.strip()]
    if len(rows) < 8:
        return None
    width = max(len(r) for r in rows)
    rows = [r.ljust(width) for r in rows]

    # Each terminal char -> 2x2 modules, each module MODULE px.
    grid_w = width * 2
    grid_h = len(rows) * 2
    img = Image.new("RGB", (grid_w * MODULE, grid_h * MODULE), "white")
    px = img.load()
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            cells = _char_cells(ch)
            for cy in range(2):
                for cx in range(2):
                    if cells[cy][cx]:
                        x0 = (x * 2 + cx) * MODULE
                        y0 = (y * 2 + cy) * MODULE
                        for yy in range(y0, y0 + MODULE):
                            for xx in range(x0, x0 + MODULE):
                                px[xx, yy] = (0, 0, 0)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def payload_to_png_b64(payload: str) -> Optional[str]:
    """Build a clean QR PNG from the raw WhatsApp pairing string."""
    try:
        import qrcode
    except ImportError:
        return None
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(payload.strip())
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def publish_qr_png(b64: str, source: str) -> None:
    _post(
        {
            "whatsapp_linked": False,
            "pairing_qr_png_base64": b64,
            "pairing_source": source,
        }
    )


def publish_pair_code(code: str) -> None:
    _post(
        {
            "whatsapp_linked": False,
            "pairing_code": code.strip().upper(),
            "pairing_source": "pair_code",
        }
    )


def publish_linked() -> None:
    _post({"whatsapp_linked": True, "clear_pairing": True})


def handle_stream(pipe, label: str) -> None:
    capturing = False
    buf: List[str] = []
    last_publish = 0.0

    for raw in iter(pipe.readline, b""):
        try:
            line = raw.decode("utf-8", errors="replace")
        except Exception:
            line = str(raw)
        sys.stdout.write(line)
        sys.stdout.flush()

        m_payload = QR_PAYLOAD.search(line)
        if m_payload:
            payload = m_payload.group(1).strip()
            png = payload_to_png_b64(payload) or None
            if png:
                publish_qr_png(png, "qr_payload")
            continue

        m_pair = PAIR_CODE.search(line)
        if m_pair:
            publish_pair_code(m_pair.group(1))
            continue

        if CONNECTED.search(line):
            publish_linked()
            capturing = False
            buf = []
            continue

        if QR_START.search(line):
            capturing = True
            buf = []
            continue

        if capturing:
            if not line.strip():
                if len(buf) >= 8:
                    now = time.time()
                    if now - last_publish > 8:
                        png = ascii_qr_to_png_b64(buf)
                        if png:
                            publish_qr_png(png, "ascii_qr")
                            last_publish = now
                capturing = False
                buf = []
            else:
                # Keep only lines that look like QR art.
                if any(ch in line for ch in ("█", "▀", "▄", "■", "▌", "▐")) or (
                    line.strip() and all(c in " █▀▄▌▐▖▗▘▝▙▛▜▟▞▚■□▪▫●○" for c in line.rstrip("\n"))
                ):
                    buf.append(line.rstrip("\n"))
                elif buf:
                    # Non-QR content ends the block.
                    if len(buf) >= 8:
                        now = time.time()
                        if now - last_publish > 8:
                            png = ascii_qr_to_png_b64(buf)
                            if png:
                                publish_qr_png(png, "ascii_qr")
                                last_publish = now
                    capturing = False
                    buf = []


def main(argv: List[str]) -> int:
    if len(argv) < 2:
        print("usage: pair_relay.py <zeroclaw> [args...]", flush=True)
        return 2
    print(f"pair_relay: publishing to {POST_URL}", flush=True)
    proc = subprocess.Popen(
        argv[1:],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=0,
    )
    assert proc.stdout is not None
    t = threading.Thread(target=handle_stream, args=(proc.stdout, "out"), daemon=True)
    t.start()
    code = proc.wait()
    t.join(timeout=2)
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
