#!/usr/bin/env python3
"""Relay ZeroClaw WhatsApp QR into Lucero Channels.

Runs: script -q -f -c "zeroclaw channel start" <logfile>
Tails that logfile (real TTY via script) and POSTs a scannable PNG to Lucero.
"""

from __future__ import annotations

import base64
import io
import os
import re
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
POST_URL = f"{API_BASE}/api/v1/channels/pairing"
LOG_PATH = os.environ.get(
    "ZEROCLAW_TTY_LOG", "/zeroclaw-data/zeroclaw-tty.log"
)

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
    print(f"pair_relay: publishing QR png source={source} len={len(b64)}", flush=True)
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
    # Strip script/ANSI noise but keep unicode QR blocks.
    clean = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", line)
    sys.stdout.write(clean if clean.endswith("\n") else clean + "\n")
    sys.stdout.flush()

    m_payload = QR_PAYLOAD.search(clean)
    if m_payload:
        png = payload_to_png_b64(m_payload.group(1).strip())
        if png:
            publish_qr_png(png, "qr_payload")
        return

    m_pair = PAIR_CODE.search(clean)
    if m_pair:
        publish_pair_code(m_pair.group(1))
        return

    if CONNECTED.search(clean):
        publish_linked()
        state["capturing"] = False
        state["buf"] = []
        return

    if QR_START.search(clean):
        state["capturing"] = True
        state["buf"] = []
        print("pair_relay: QR header detected", flush=True)
        return

    if state["capturing"]:
        if not clean.strip():
            state["last_publish"] = _flush_qr(state["buf"], state["last_publish"])
            state["capturing"] = False
            state["buf"] = []
        elif _looks_like_qr_line(clean):
            state["buf"].append(clean.rstrip("\n"))
        elif state["buf"]:
            state["last_publish"] = _flush_qr(state["buf"], state["last_publish"])
            state["capturing"] = False
            state["buf"] = []
        return

    if _looks_like_qr_line(clean) and ("█" in clean or "▀" in clean):
        state["capturing"] = True
        state["buf"] = [clean.rstrip("\n")]


def main() -> int:
    print(f"pair_relay: publishing to {POST_URL}", flush=True)
    print(f"pair_relay: api_key_set={bool(API_KEY)} pillow={Image is not None}", flush=True)
    print(f"pair_relay: tty log {LOG_PATH}", flush=True)
    publish_online()

    # Truncate previous log.
    open(LOG_PATH, "wb").close()

    cmd = f"zeroclaw channel start"
    proc = subprocess.Popen(
        ["script", "-q", "-f", "-c", cmd, LOG_PATH],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"pair_relay: started pid={proc.pid} via script: {cmd}", flush=True)

    state = {"capturing": False, "buf": [], "last_publish": 0.0}
    leftover = ""
    last_hb = time.time()
    last_size = 0
    idle_loops = 0

    with open(LOG_PATH, "rb") as fh:
        while True:
            chunk = fh.read()
            if chunk:
                idle_loops = 0
                text = leftover + chunk.decode("utf-8", errors="replace")
                # script may use \r
                text = text.replace("\r\n", "\n").replace("\r", "\n")
                lines = text.splitlines(keepends=True)
                if lines and not text.endswith("\n"):
                    leftover = lines.pop()
                else:
                    leftover = ""
                for line in lines:
                    process_line(line, state)
                last_size = fh.tell()
            else:
                idle_loops += 1
                time.sleep(0.4)

            now = time.time()
            if now - last_hb > 25:
                publish_online()
                size = os.path.getsize(LOG_PATH) if os.path.exists(LOG_PATH) else 0
                print(
                    f"pair_relay: heartbeat log_bytes={size} capturing={state['capturing']} buf={len(state['buf'])} alive={proc.poll() is None}",
                    flush=True,
                )
                last_hb = now

            if state["capturing"] and state["buf"] and idle_loops > 8:
                state["last_publish"] = _flush_qr(state["buf"], state["last_publish"])
                state["capturing"] = False
                state["buf"] = []

            code = proc.poll()
            if code is not None:
                # Final drain
                time.sleep(0.5)
                chunk = fh.read()
                if chunk:
                    text = leftover + chunk.decode("utf-8", errors="replace")
                    text = text.replace("\r\n", "\n").replace("\r", "\n")
                    for line in text.splitlines(keepends=True):
                        process_line(line, state)
                print(f"pair_relay: script/zeroclaw exited code={code}", flush=True)
                return code


if __name__ == "__main__":
    raise SystemExit(main())
