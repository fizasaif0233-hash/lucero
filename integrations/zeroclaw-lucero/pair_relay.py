#!/usr/bin/env python3
"""Relay ZeroClaw WhatsApp QR / pair-code into Lucero Channels dashboard.

Runs ZeroClaw under a PTY so Rust line-buffers QR output (pipes stay silent).
Captures terminal QR art / payload / pair code and POSTs a scannable PNG to
Lucero so the client can scan from Dashboard → Channels.
"""

from __future__ import annotations

import base64
import io
import os
import pty
import re
import select
import subprocess
import sys
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
CONNECTED = re.compile(
    r"connected successfully|whatsapp.*linked|Logged in|device linked", re.I
)
QR_CHARS = set(" █▀▄▌▐▖▗▘▝▙▛▜▟▞▚■□▪▫●○")

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
    try:
        import qrcode
    except ImportError:
        return None
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2
    )
    qr.add_data(payload.strip())
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def publish_qr_png(b64: str, source: str) -> None:
    print(f"pair_relay: publishing QR png source={source} bytes={len(b64)}", flush=True)
    _post(
        {
            "whatsapp_linked": False,
            "pairing_qr_png_base64": b64,
            "pairing_source": source,
            "online": True,
        }
    )


def publish_pair_code(code: str) -> None:
    print(f"pair_relay: publishing pair code {code}", flush=True)
    _post(
        {
            "whatsapp_linked": False,
            "pairing_code": code.strip().upper(),
            "pairing_source": "pair_code",
            "online": True,
        }
    )


def publish_linked() -> None:
    print("pair_relay: WhatsApp linked", flush=True)
    _post({"whatsapp_linked": True, "clear_pairing": True, "online": True})


def publish_online() -> None:
    _post({"whatsapp_linked": False, "online": True})


def _looks_like_qr_line(line: str) -> bool:
    s = line.rstrip("\n")
    if len(s.strip()) < 10:
        return False
    if any(ch in s for ch in ("█", "▀", "▄", "■", "▌", "▐")):
        return True
    return bool(s.strip()) and all(c in QR_CHARS for c in s)


def _flush_qr(buf: List[str], last_publish: float) -> float:
    if len(buf) < 8:
        return last_publish
    now = time.time()
    if now - last_publish < 5:
        return last_publish
    png = ascii_qr_to_png_b64(buf)
    if png:
        publish_qr_png(png, "ascii_qr")
        return now
    print(f"pair_relay: failed to render QR from {len(buf)} lines", flush=True)
    return last_publish


def process_line(line: str, state: dict) -> None:
    sys.stdout.write(line)
    sys.stdout.flush()

    m_payload = QR_PAYLOAD.search(line)
    if m_payload:
        png = payload_to_png_b64(m_payload.group(1).strip())
        if png:
            publish_qr_png(png, "qr_payload")
        return

    m_pair = PAIR_CODE.search(line)
    if m_pair:
        publish_pair_code(m_pair.group(1))
        return

    if CONNECTED.search(line):
        publish_linked()
        state["capturing"] = False
        state["buf"] = []
        return

    if QR_START.search(line):
        state["capturing"] = True
        state["buf"] = []
        return

    if state["capturing"]:
        if not line.strip():
            state["last_publish"] = _flush_qr(state["buf"], state["last_publish"])
            state["capturing"] = False
            state["buf"] = []
        elif _looks_like_qr_line(line):
            state["buf"].append(line.rstrip("\n"))
        elif state["buf"]:
            state["last_publish"] = _flush_qr(state["buf"], state["last_publish"])
            state["capturing"] = False
            state["buf"] = []
        return

    # Some builds print QR art without the header line.
    if _looks_like_qr_line(line) and ("█" in line or "▀" in line):
        state["capturing"] = True
        state["buf"] = [line.rstrip("\n")]


def main(argv: List[str]) -> int:
    if len(argv) < 2:
        print("usage: pair_relay.py <zeroclaw> [args...]", flush=True)
        return 2

    print(f"pair_relay: publishing to {POST_URL}", flush=True)
    print(f"pair_relay: api_key_set={bool(API_KEY)} pillow={Image is not None}", flush=True)
    publish_online()

    master, slave = pty.openpty()
    proc = subprocess.Popen(
        argv[1:],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        close_fds=True,
    )
    os.close(slave)

    state = {"capturing": False, "buf": [], "last_publish": 0.0}
    leftover = ""
    last_hb = time.time()

    try:
        while True:
            if proc.poll() is not None:
                # Drain remaining output.
                while True:
                    ready, _, _ = select.select([master], [], [], 0.2)
                    if not ready:
                        break
                    chunk = os.read(master, 4096)
                    if not chunk:
                        break
                    text = leftover + chunk.decode("utf-8", errors="replace")
                    lines = text.splitlines(keepends=True)
                    if lines and not text.endswith(("\n", "\r")):
                        leftover = lines.pop()
                    else:
                        leftover = ""
                    for line in lines:
                        process_line(line, state)
                break

            ready, _, _ = select.select([master], [], [], 1.0)
            now = time.time()
            if now - last_hb > 30:
                publish_online()
                last_hb = now

            if not ready:
                # If we were capturing and went quiet, flush.
                if state["capturing"] and state["buf"] and now - state["last_publish"] > 3:
                    state["last_publish"] = _flush_qr(state["buf"], state["last_publish"])
                    state["capturing"] = False
                    state["buf"] = []
                continue

            chunk = os.read(master, 4096)
            if not chunk:
                break
            text = leftover + chunk.decode("utf-8", errors="replace")
            lines = text.splitlines(keepends=True)
            if lines and not text.endswith(("\n", "\r")):
                leftover = lines.pop()
            else:
                leftover = ""
            for line in lines:
                process_line(line, state)
    finally:
        try:
            os.close(master)
        except OSError:
            pass

    code = proc.wait()
    print(f"pair_relay: zeroclaw exited code={code}", flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
