"""Print-ready flyer / poster / social composition → PNG + PDF."""

from __future__ import annotations

import io
from pathlib import Path
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

_FONT_DIR = Path(__file__).resolve().parent / "fonts"


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    size = max(14, int(size))
    bundled = [
        _FONT_DIR / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
        _FONT_DIR / ("DejaVuSerif-Bold.ttf" if bold else "DejaVuSerif.ttf"),
    ]
    system = [
        "C:/Windows/Fonts/georgia.ttf" if not bold else "C:/Windows/Fonts/georgiab.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in [*bundled, *system]:
        try:
            return ImageFont.truetype(str(path), size=size)
        except Exception:
            continue
    raise RuntimeError(
        "No TrueType fonts available for print compose — ship fonts in app/media/fonts."
    )


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
    overlay_rgba = (0, 0, 0, 150) if theme == "black_gold" else (8, 40, 30, 140)
    if url:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content)).convert("RGB")
            img = img.resize((w, h), Image.Resampling.LANCZOS)
            overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)
            # Gradient band for readable type over FLUX art
            od.rectangle((0, int(h * 0.48), w, h), fill=overlay_rgba)
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
            return img

    img = Image.new("RGB", (w, h), base)
    draw = ImageDraw.Draw(img)
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for i, alpha in enumerate((36, 22, 12)):
        pad = int(w * (0.06 + i * 0.05))
        gd.ellipse(
            (pad, int(h * 0.04) + pad // 2, w - pad, int(h * 0.52) - pad // 3),
            fill=(201, 162, 39, alpha),
        )
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    draw = ImageDraw.Draw(img)
    border = max(4, w // 180)
    inset = max(20, w // 36)
    draw.rectangle((inset, inset, w - inset, h - inset), outline=GOLD, width=border)
    draw.rectangle(
        (
            inset + border * 2,
            inset + border * 2,
            w - inset - border * 2,
            h - inset - border * 2,
        ),
        outline=SOFT_GOLD if theme == "black_gold" else CREAM,
        width=max(1, border // 2),
    )
    return img


class PrintComposer:
    """Compose print / social assets the owner can download and use."""

    def __init__(self) -> None:
        self._storage = GeneratedStorage()

    async def compose_flyer(
        self,
        *,
        user_id: str,
        copy: Dict[str, str],
        background_url: Optional[str] = None,
        title: str = "Print-ready flyer",
        size: Tuple[int, int] = (2550, 3300),
        theme: str = "agave",
        require_background: bool = False,
    ) -> Dict[str, Any]:
        if require_background and not background_url:
            raise ValueError("Replicate artwork URL required for this layout")

        w, h = size
        # Square social vs letter print — use absolute sizes so type stays readable
        square = abs(w - h) < 80
        if square:
            s = w / 1080.0
            title_px, sub_px, body_px, cta_px, brand_px = (
                int(72 * s),
                int(36 * s),
                int(30 * s),
                int(34 * s),
                int(28 * s),
            )
            start_y_ratio = 0.52
            margin = int(56 * s)
        else:
            s = w / 2550.0
            title_px, sub_px, body_px, cta_px, brand_px = (
                int(140 * s),
                int(58 * s),
                int(48 * s),
                int(54 * s),
                int(44 * s),
            )
            start_y_ratio = 0.42 if background_url else 0.26
            margin = int(160 * s)

        img = await _load_bg(background_url, size, theme=theme)
        draw = ImageDraw.Draw(img)

        title_font = _font(title_px, bold=True)
        sub_font = _font(sub_px, bold=False)
        body_font = _font(body_px, bold=False)
        cta_font = _font(cta_px, bold=True)
        brand_font = _font(brand_px, bold=True)

        text_w = w - margin * 2
        text_main = CREAM
        text_accent = GOLD

        brand = copy.get("brand") or "Blue Prince21 McKinzy"
        draw.text(
            (margin, int(48 * (w / 1080.0 if square else s))),
            brand.upper(),
            fill=text_accent,
            font=brand_font,
        )

        y = int(h * start_y_ratio)
        headline = copy.get("headline") or "Blue Prince21 McKinzy"
        for line in _wrap(draw, headline, title_font, text_w)[:3]:
            draw.text((margin, y), line, fill=text_main, font=title_font)
            y += int(title_px * 1.15)

        y += int(12 * (w / 1080.0 if square else s))
        subhead = copy.get("subhead") or ""
        for line in _wrap(draw, subhead, sub_font, text_w)[:2]:
            draw.text((margin, y), line, fill=text_accent, font=sub_font)
            y += int(sub_px * 1.2)

        # Social: keep body short; print: allow more lines
        body = copy.get("body") or ""
        if not square:
            y += int(24 * s)
            body_max_y = h - int(420 * s)
            for line in _wrap(draw, body, body_font, text_w):
                if y + int(body_px * 1.15) > body_max_y:
                    break
                draw.text((margin, y), line, fill=text_main, font=body_font)
                y += int(body_px * 1.15)

        cta = copy.get("cta") or "anthonywarrenmckinzy.com"
        bar_h = int(110 * (w / 1080.0 if square else s * 1.1))
        bar_y = h - int(200 * (w / 1080.0 if square else s * 1.15))
        draw.rectangle((margin, bar_y, w - margin, bar_y + bar_h), fill=GOLD)
        cta_lines = _wrap(draw, cta, cta_font, text_w - 40)[:2]
        line_h = int(cta_px * 1.15)
        cta_y = bar_y + max(8, (bar_h - len(cta_lines) * line_h) // 2)
        for line in cta_lines:
            tw = draw.textlength(line, font=cta_font)
            draw.text(((w - tw) / 2, cta_y), line, fill=CHARCOAL, font=cta_font)
            cta_y += line_h

        tag = copy.get("tagline") or "Drink it. Trade it. Own it."
        draw.text(
            (margin, h - int(70 * (w / 1080.0 if square else s))),
            tag,
            fill=text_main,
            font=brand_font,
        )

        return await self._export(user_id=user_id, img=img, title=title, theme=theme)

    async def _export(
        self,
        *,
        user_id: str,
        img: Image.Image,
        title: str,
        theme: str,
    ) -> Dict[str, Any]:
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
        assets: list[dict] = [
            {
                "kind": "image",
                "title": f"{title} (PNG)",
                "storage_path": path,
                "public_url": public,
                "mime": "image/png",
                "byte_size": len(png_bytes),
                "meta": {"print_ready": True, "dpi": 300, "format": "png", "theme": theme},
            }
        ]

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
