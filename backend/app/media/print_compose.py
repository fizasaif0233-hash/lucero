"""Print-ready flyer / poster composition → PNG + PDF (download & print)."""

from __future__ import annotations

import io
from typing import Any, Dict, Optional, Tuple

import httpx
from PIL import Image, ImageDraw, ImageFont

from app.media.storage import GeneratedStorage


# Brand palette
GREEN = (11, 61, 46)
GOLD = (201, 162, 39)
CREAM = (245, 240, 230)
CHARCOAL = (26, 26, 26)
BLACK = (8, 8, 8)
WHITE = (255, 255, 255)
SOFT_GOLD = (232, 200, 110)


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    size = max(12, int(size))
    candidates = [
        "C:/Windows/Fonts/georgia.ttf" if not bold else "C:/Windows/Fonts/georgiab.ttf",
        "C:/Windows/Fonts/times.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            continue
    # Last resort — still scale-ish via default
    return ImageFont.load_default()


def _wrap(
    draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_w: int
) -> list[str]:
    words = (text or "").split()
    if not words:
        return [""]
    lines: list[str] = []
    cur = words[0]
    for w in words[1:]:
        trial = f"{cur} {w}"
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


async def _load_bg(
    url: Optional[str],
    size: Tuple[int, int],
    *,
    theme: str = "agave",
) -> Image.Image:
    w, h = size
    base = BLACK if theme == "black_gold" else GREEN
    overlay_rgba = (0, 0, 0, 165) if theme == "black_gold" else (11, 61, 46, 155)
    if url:
        try:
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                img = img.resize((w, h), Image.Resampling.LANCZOS)
                overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                od = ImageDraw.Draw(overlay)
                od.rectangle((0, int(h * 0.42), w, h), fill=overlay_rgba)
                img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
                return img
        except Exception:
            pass

    # Brand canvas (no AI art) — richer than a flat fill
    img = Image.new("RGB", (w, h), base)
    draw = ImageDraw.Draw(img)
    # Soft radial-ish gold glow via stacked ellipses
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for i, alpha in enumerate((28, 18, 10)):
        pad = int(w * (0.08 + i * 0.06))
        gd.ellipse(
            (pad, int(h * 0.05) + pad // 2, w - pad, int(h * 0.55) - pad // 3),
            fill=(201, 162, 39, alpha),
        )
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    draw = ImageDraw.Draw(img)
    border = max(4, w // 200)
    inset = max(24, w // 40)
    draw.rectangle(
        (inset, inset, w - inset, h - inset), outline=GOLD, width=border
    )
    draw.rectangle(
        (inset + border * 2, inset + border * 2, w - inset - border * 2, h - inset - border * 2),
        outline=SOFT_GOLD if theme == "black_gold" else CREAM,
        width=max(1, border // 2),
    )
    # Decorative gold rule
    rule_y = int(h * 0.18)
    draw.line((inset * 2, rule_y, w - inset * 2, rule_y), fill=GOLD, width=max(2, border // 2))
    return img


class PrintComposer:
    """Compose US Letter / flyer print assets the owner can send to a printer."""

    def __init__(self) -> None:
        self._storage = GeneratedStorage()

    async def compose_flyer(
        self,
        *,
        user_id: str,
        copy: Dict[str, str],
        background_url: Optional[str] = None,
        title: str = "Print-ready flyer",
        size: Tuple[int, int] = (2550, 3300),  # ~8.5x11 @ 300dpi
        theme: str = "agave",
    ) -> Dict[str, Any]:
        w, h = size
        # Scale typography from letter reference (2550px wide)
        s = max(0.45, w / 2550.0)
        img = await _load_bg(background_url, size, theme=theme)
        draw = ImageDraw.Draw(img)

        title_font = _font(int(128 * s), bold=True)
        sub_font = _font(int(56 * s), bold=False)
        body_font = _font(int(46 * s), bold=False)
        cta_font = _font(int(52 * s), bold=True)
        brand_font = _font(int(42 * s), bold=True)

        margin = int(160 * s)
        text_w = w - margin * 2
        text_main = CREAM
        text_accent = GOLD

        brand = copy.get("brand") or "Blue Prince21 McKinzy"
        draw.text((margin, int(100 * s)), brand.upper(), fill=text_accent, font=brand_font)

        # Start copy lower-third so upper area can show bottle art / glow
        y = int(h * (0.40 if background_url else 0.28))

        headline = copy.get("headline") or "Blue Prince21 McKinzy"
        for line in _wrap(draw, headline, title_font, text_w)[:4]:
            draw.text((margin, y), line, fill=text_main, font=title_font)
            y += int(130 * s)

        y += int(16 * s)
        subhead = copy.get("subhead") or ""
        for line in _wrap(draw, subhead, sub_font, text_w)[:3]:
            draw.text((margin, y), line, fill=text_accent, font=sub_font)
            y += int(66 * s)

        y += int(28 * s)
        body = copy.get("body") or ""
        # Cap body length so it doesn't overrun the CTA
        body_max_y = h - int(420 * s)
        for line in _wrap(draw, body, body_font, text_w):
            if y + int(54 * s) > body_max_y:
                break
            draw.text((margin, y), line, fill=text_main, font=body_font)
            y += int(54 * s)

        # CTA bar
        cta = copy.get("cta") or "anthonywarrenmckinzy.com"
        bar_h = int(150 * s)
        bar_y = h - int(300 * s)
        draw.rectangle((margin, bar_y, w - margin, bar_y + bar_h), fill=GOLD)
        cta_lines = _wrap(draw, cta, cta_font, text_w - int(80 * s))[:2]
        line_h = int(58 * s)
        cta_y = bar_y + (bar_h - len(cta_lines) * line_h) // 2
        for line in cta_lines:
            tw = draw.textlength(line, font=cta_font)
            draw.text(((w - tw) / 2, cta_y), line, fill=CHARCOAL, font=cta_font)
            cta_y += line_h

        tag = copy.get("tagline") or "Drink it. Trade it. Own it."
        draw.text(
            (margin, h - int(110 * s)), tag, fill=text_main, font=brand_font
        )

        png_buf = io.BytesIO()
        img.save(png_buf, format="PNG", dpi=(300, 300))
        png_bytes = png_buf.getvalue()

        path, public = await self._storage.upload_bytes(
            user_id=user_id,
            data=png_bytes,
            ext="png",
            mime="image/png",
            folder="print",
        )
        assets = [
            {
                "kind": "image",
                "title": f"{title} (PNG 300dpi)",
                "storage_path": path,
                "public_url": public,
                "mime": "image/png",
                "byte_size": len(png_bytes),
                "meta": {"print_ready": True, "dpi": 300, "format": "png", "theme": theme},
            }
        ]

        # PDF via reportlab
        try:
            pdf_bytes = self._png_to_pdf(png_bytes, page_size="letter")
            pdf_path, pdf_url = await self._storage.upload_bytes(
                user_id=user_id,
                data=pdf_bytes,
                ext="pdf",
                mime="application/pdf",
                folder="print",
            )
            assets.append(
                {
                    "kind": "pdf",
                    "title": f"{title} (PDF)",
                    "storage_path": pdf_path,
                    "public_url": pdf_url,
                    "mime": "application/pdf",
                    "byte_size": len(pdf_bytes),
                    "meta": {"print_ready": True, "format": "pdf", "theme": theme},
                }
            )
            primary = pdf_url
        except Exception:
            primary = public

        return {"assets": assets, "primary_url": primary, "png_url": public}

    @staticmethod
    def _png_to_pdf(png_bytes: bytes, page_size: str = "letter") -> bytes:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas

        page = letter if page_size == "letter" else A4
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=page)
        pw, ph = page
        img = ImageReader(io.BytesIO(png_bytes))
        c.drawImage(img, 0, 0, width=pw, height=ph, preserveAspectRatio=True, anchor="c")
        c.showPage()
        c.save()
        return buf.getvalue()
