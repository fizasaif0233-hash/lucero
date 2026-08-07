"""Print-ready A4 flyer / poster / social composition → PNG + PDF."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from PIL import Image, ImageDraw, ImageFont

from app.core.brand import PRIMARY_WEBSITE

# Brand palette
GREEN = (11, 61, 46)
GOLD = (201, 162, 39)
CREAM = (245, 240, 230)
CHARCOAL = (26, 26, 26)
BLACK = (8, 8, 8)
SOFT_GOLD = (232, 200, 110)
NAVY = (12, 22, 40)

# A4 @ 300 DPI (print-ready)
A4_300_DPI = (2480, 3508)

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


def _fit_cover(src: Image.Image, box: Tuple[int, int]) -> Image.Image:
    tw, th = box
    sw, sh = src.size
    scale = max(tw / sw, th / sh)
    nw, nh = int(sw * scale), int(sh * scale)
    resized = src.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - tw) // 2
    top = (nh - th) // 2
    return resized.crop((left, top, left + tw, top + th))


def _fit_contain(src: Image.Image, box: Tuple[int, int], fill: Tuple[int, int, int]) -> Image.Image:
    tw, th = box
    canvas = Image.new("RGB", (tw, th), fill)
    sw, sh = src.size
    scale = min(tw / sw, th / sh)
    nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
    resized = src.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas.paste(resized, ((tw - nw) // 2, (th - nh) // 2))
    return canvas


async def _fetch_image(url: str) -> Image.Image:
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return Image.open(io.BytesIO(resp.content)).convert("RGB")


def _make_qr(url: str, box: int, *, dark: Tuple[int, int, int], light: Tuple[int, int, int]) -> Image.Image:
    try:
        import qrcode
        from qrcode.constants import ERROR_CORRECT_M

        qr = qrcode.QRCode(
            version=None,
            error_correction=ERROR_CORRECT_M,
            box_size=10,
            border=1,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color=dark, back_color=light).convert("RGB")
        return img.resize((box, box), Image.Resampling.NEAREST)
    except Exception:
        # Fallback mark if qrcode isn't installed yet
        img = Image.new("RGB", (box, box), light)
        d = ImageDraw.Draw(img)
        pad = max(4, box // 16)
        d.rectangle((pad, pad, box - pad, box - pad), outline=dark, width=max(2, box // 40))
        d.text((pad * 2, box // 2 - 8), "QR", fill=dark)
        return img


def _draw_logo_mark(
    draw: ImageDraw.ImageDraw,
    origin: Tuple[int, int],
    size: int,
    *,
    accent: Tuple[int, int, int],
    fill: Tuple[int, int, int],
) -> None:
    x, y = origin
    draw.ellipse((x, y, x + size, y + size), outline=accent, width=max(3, size // 18))
    draw.ellipse(
        (x + size // 8, y + size // 8, x + size - size // 8, y + size - size // 8),
        outline=accent,
        width=max(2, size // 28),
    )
    # Simple crown hint
    cx, cy = x + size // 2, y + size // 3
    pts = [
        (cx - size // 4, cy + size // 8),
        (cx - size // 5, cy - size // 10),
        (cx - size // 12, cy + size // 14),
        (cx, cy - size // 8),
        (cx + size // 12, cy + size // 14),
        (cx + size // 5, cy - size // 10),
        (cx + size // 4, cy + size // 8),
    ]
    draw.polygon(pts, fill=accent)
    mark_font = _font(max(18, size // 4), bold=True)
    label = "BP21"
    tw = draw.textlength(label, font=mark_font)
    draw.text((x + (size - tw) / 2, y + size * 0.58), label, fill=fill, font=mark_font)


def _parse_features(copy: Dict[str, str]) -> List[str]:
    raw = copy.get("features") or ""
    if raw:
        parts = re_split_features(raw)
        if parts:
            return parts[:5]
    body = copy.get("body") or ""
    # Split body into short feature-like lines when no explicit features
    chunks = [c.strip(" •-\t") for c in re_split_features(body)]
    chunks = [c for c in chunks if 8 <= len(c) <= 90]
    if chunks:
        return chunks[:4]
    return [
        "100% additive-free tequila",
        "Blockchain-verified provenance",
        "Barrel-backed ownership",
        "Drink it. Trade it. Own it.",
    ]


def re_split_features(text: str) -> List[str]:
    import re

    lines = re.findall(r"(?:^|\n)\s*[-*•]\s*(.+)", text or "")
    if lines:
        return [re.sub(r"\s+", " ", x).strip() for x in lines if x.strip()]
    # Semicolon / pipe / sentence splits
    parts = re.split(r"[;\n|]+|(?<=\.)\s+", text or "")
    return [re.sub(r"\s+", " ", p).strip(" .") for p in parts if p.strip()]


class PrintComposer:
    """Compose print / social assets the owner can download and use."""

    def __init__(self) -> None:
        from app.media.storage import GeneratedStorage

        self._storage = GeneratedStorage()

    async def compose_flyer(
        self,
        *,
        user_id: str,
        copy: Dict[str, str],
        background_url: Optional[str] = None,
        title: str = "Print-ready flyer",
        size: Tuple[int, int] = A4_300_DPI,
        theme: str = "agave",
        require_background: bool = False,
        page_size: str = "a4",
    ) -> Dict[str, Any]:
        if require_background and not background_url:
            raise ValueError("Replicate artwork URL required for this layout")

        w, h = size
        square = abs(w - h) < 80
        landscape = w > h * 1.15
        if square or landscape:
            img = await self._compose_social(
                copy=copy, background_url=background_url, size=size, theme=theme
            )
            export_page = "square" if square else "landscape"
        else:
            img = await self._compose_print_a4(
                copy=copy, product_url=background_url, size=size, theme=theme
            )
            export_page = page_size

        return await self._export(
            user_id=user_id,
            img=img,
            title=title,
            theme=theme,
            page_size=export_page,
        )

    async def _compose_social(
        self,
        *,
        copy: Dict[str, str],
        background_url: Optional[str],
        size: Tuple[int, int],
        theme: str,
    ) -> Image.Image:
        w, h = size
        s = w / 1080.0
        if background_url:
            src = await _fetch_image(background_url)
            img = _fit_cover(src, (w, h))
            overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)
            od.rectangle((0, int(h * 0.52), w, h), fill=(0, 0, 0, 160))
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        else:
            base = BLACK if theme == "black_gold" else GREEN
            img = Image.new("RGB", (w, h), base)

        draw = ImageDraw.Draw(img)
        margin = int(56 * s)
        brand_font = _font(int(28 * s), bold=True)
        title_font = _font(int(64 * s), bold=True)
        sub_font = _font(int(30 * s), bold=False)
        cta_font = _font(int(32 * s), bold=True)

        brand = copy.get("brand") or "Blue Prince21 McKinzy"
        draw.text((margin, int(40 * s)), brand.upper(), fill=GOLD, font=brand_font)

        y = int(h * 0.58)
        headline = copy.get("headline") or brand
        for line in _wrap(draw, headline, title_font, w - margin * 2)[:3]:
            draw.text((margin, y), line, fill=CREAM, font=title_font)
            y += int(64 * s * 1.12)

        subhead = copy.get("subhead") or ""
        for line in _wrap(draw, subhead, sub_font, w - margin * 2)[:2]:
            draw.text((margin, y), line, fill=SOFT_GOLD, font=sub_font)
            y += int(30 * s * 1.2)

        cta = copy.get("cta") or PRIMARY_WEBSITE.replace("https://www.", "")
        bar_h = int(88 * s)
        bar_y = h - int(140 * s)
        draw.rectangle((margin, bar_y, w - margin, bar_y + bar_h), fill=GOLD)
        tw = draw.textlength(cta, font=cta_font)
        draw.text(((w - tw) / 2, bar_y + (bar_h - int(32 * s)) // 2), cta, fill=CHARCOAL, font=cta_font)
        return img

    async def _compose_print_a4(
        self,
        *,
        copy: Dict[str, str],
        product_url: Optional[str],
        size: Tuple[int, int],
        theme: str,
    ) -> Image.Image:
        """Full marketing flyer: logo, headline, product, features, CTA, QR, contact."""
        w, h = size
        s = w / 2480.0
        base = BLACK if theme == "black_gold" else GREEN
        panel = NAVY if theme == "black_gold" else (8, 40, 30)
        img = Image.new("RGB", (w, h), base)
        draw = ImageDraw.Draw(img)

        margin = int(140 * s)
        content_w = w - margin * 2
        accent = GOLD
        text_main = CREAM
        muted = SOFT_GOLD

        # Outer double frame
        border = max(4, int(8 * s))
        draw.rectangle(
            (int(60 * s), int(60 * s), w - int(60 * s), h - int(60 * s)),
            outline=accent,
            width=border,
        )
        draw.rectangle(
            (int(90 * s), int(90 * s), w - int(90 * s), h - int(90 * s)),
            outline=SOFT_GOLD,
            width=max(1, border // 2),
        )

        # ---- Header: logo + brand ----
        logo_size = int(160 * s)
        y = int(140 * s)
        _draw_logo_mark(
            draw,
            (margin, y),
            logo_size,
            accent=accent,
            fill=text_main,
        )
        brand = copy.get("brand") or "Blue Prince21 McKinzy"
        brand_font = _font(int(54 * s), bold=True)
        tag_font = _font(int(34 * s), bold=False)
        draw.text(
            (margin + logo_size + int(36 * s), y + int(28 * s)),
            brand.upper(),
            fill=accent,
            font=brand_font,
        )
        draw.text(
            (margin + logo_size + int(36 * s), y + int(95 * s)),
            copy.get("tagline") or "Drink it. Trade it. Own it.",
            fill=muted,
            font=tag_font,
        )
        y = y + logo_size + int(50 * s)

        # Divider
        draw.line((margin, y, w - margin, y), fill=accent, width=max(2, int(3 * s)))
        y += int(48 * s)

        # ---- Headline + subhead ----
        title_font = _font(int(88 * s), bold=True)
        sub_font = _font(int(40 * s), bold=False)
        headline = copy.get("headline") or brand
        for line in _wrap(draw, headline, title_font, content_w)[:3]:
            draw.text((margin, y), line, fill=text_main, font=title_font)
            y += int(88 * s * 1.1)
        y += int(8 * s)
        subhead = copy.get("subhead") or "Premium Additive-Free Tequila"
        for line in _wrap(draw, subhead, sub_font, content_w)[:2]:
            draw.text((margin, y), line, fill=muted, font=sub_font)
            y += int(40 * s * 1.15)
        y += int(28 * s)
        photo_top = y

        # Reserve footer + CTA + features from the bottom so the product fills the middle
        features = _parse_features(copy)
        feat_title_font = _font(int(36 * s), bold=True)
        body_font = _font(int(34 * s), bold=False)
        cta_font = _font(int(46 * s), bold=True)
        bar_h = int(110 * s)
        footer_h = int(400 * s)
        feat_block_h = int(56 * s) + len(features) * int(52 * s) + int(24 * s)
        cta_top = h - footer_h - bar_h - int(36 * s)
        feat_top = cta_top - feat_block_h - int(24 * s)
        photo_bottom = feat_top - int(36 * s)
        photo_h = max(int(900 * s), photo_bottom - photo_top)
        photo_box = (content_w, photo_h)
        photo_fill = panel
        if product_url:
            try:
                product = await _fetch_image(product_url)
                photo = _fit_contain(product, photo_box, photo_fill)
            except Exception:
                photo = Image.new("RGB", photo_box, photo_fill)
        else:
            photo = Image.new("RGB", photo_box, photo_fill)
            pd = ImageDraw.Draw(photo)
            pd.text(
                (photo_box[0] // 3, photo_box[1] // 2),
                "Product art",
                fill=GOLD,
                font=_font(int(48 * s), bold=True),
            )

        frame_pad = int(10 * s)
        frame = Image.new(
            "RGB",
            (photo_box[0] + frame_pad * 2, photo_box[1] + frame_pad * 2),
            accent,
        )
        frame.paste(photo, (frame_pad, frame_pad))
        img.paste(frame, (margin - frame_pad, photo_top))

        # ---- Features (above CTA) ----
        y = feat_top
        draw.text((margin, y), "FEATURES", fill=accent, font=feat_title_font)
        y += int(50 * s)
        for feat in features:
            bx = margin + int(12 * s)
            by = y + int(8 * s)
            diamond = [
                (bx, by + int(10 * s)),
                (bx + int(10 * s), by),
                (bx + int(20 * s), by + int(10 * s)),
                (bx + int(10 * s), by + int(20 * s)),
            ]
            draw.polygon(diamond, fill=accent)
            text_x = margin + int(48 * s)
            for line in _wrap(draw, feat, body_font, content_w - int(60 * s))[:2]:
                draw.text((text_x, y), line, fill=text_main, font=body_font)
                y += int(34 * s * 1.2)
            y += int(8 * s)

        # ---- CTA bar (pinned above footer) ----
        cta = copy.get("cta") or "Order Now — Limited Release"
        y = cta_top
        draw.rectangle((margin, y, w - margin, y + bar_h), fill=accent)
        cta_lines = _wrap(draw, cta, cta_font, content_w - int(80 * s))[:2]
        line_h = int(46 * s * 1.12)
        cta_y = y + max(int(14 * s), (bar_h - len(cta_lines) * line_h) // 2)
        for line in cta_lines:
            tw = draw.textlength(line, font=cta_font)
            draw.text(((w - tw) / 2, cta_y), line, fill=CHARCOAL, font=cta_font)
            cta_y += line_h

        # ---- Footer: QR + website + contact ----
        website = (copy.get("website") or PRIMARY_WEBSITE).strip()
        if website and not website.startswith("http"):
            website = "https://" + website.lstrip("/")
        contact = (copy.get("contact") or "").strip()
        site_display = website.replace("https://www.", "").replace("https://", "")
        if not contact or contact.lower() in {site_display.lower(), website.lower()}:
            contact = ""
        qr_size = int(260 * s)
        footer_y = h - footer_h + int(20 * s)
        qr = _make_qr(website, qr_size, dark=CHARCOAL, light=CREAM)
        qr_matte = Image.new(
            "RGB", (qr_size + int(24 * s), qr_size + int(24 * s)), accent
        )
        qr_matte.paste(qr, (int(12 * s), int(12 * s)))
        img.paste(qr_matte, (margin, footer_y))

        info_x = margin + qr_matte.size[0] + int(48 * s)
        info_font = _font(int(36 * s), bold=True)
        small_font = _font(int(30 * s), bold=False)
        draw.text(
            (info_x, footer_y + int(30 * s)), "SCAN TO VISIT", fill=accent, font=info_font
        )
        draw.text(
            (info_x, footer_y + int(90 * s)),
            site_display,
            fill=text_main,
            font=small_font,
        )
        next_y = footer_y + int(145 * s)
        if contact:
            draw.text((info_x, next_y), contact, fill=muted, font=small_font)
            next_y += int(55 * s)
        draw.text(
            (info_x, next_y),
            copy.get("tagline") or "Drink it. Trade it. Own it.",
            fill=text_main,
            font=info_font,
        )
        draw.text(
            (margin, h - int(120 * s)),
            "Print-ready A4 · 300 DPI · Blue Prince21 McKinzy",
            fill=muted,
            font=_font(int(24 * s), bold=False),
        )
        return img

    async def _export(
        self,
        *,
        user_id: str,
        img: Image.Image,
        title: str,
        theme: str,
        page_size: str = "a4",
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
                "meta": {
                    "print_ready": True,
                    "dpi": 300,
                    "format": "png",
                    "theme": theme,
                    "page": page_size,
                },
            }
        ]

        try:
            pdf_page = "a4" if page_size != "square" else "letter"
            pdf_bytes = self._png_to_pdf(png_bytes, page_size=pdf_page)
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
                    "meta": {
                        "print_ready": True,
                        "format": "pdf",
                        "theme": theme,
                        "page": pdf_page,
                        "dpi": 300,
                    },
                }
            )
            primary = pdf_url
        except Exception:
            primary = public

        return {"assets": assets, "primary_url": primary, "png_url": public}

    @staticmethod
    def _png_to_pdf(png_bytes: bytes, page_size: str = "a4") -> bytes:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas

        page = A4 if page_size == "a4" else letter
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=page)
        pw, ph = page
        img = ImageReader(io.BytesIO(png_bytes))
        c.drawImage(img, 0, 0, width=pw, height=ph, preserveAspectRatio=False, anchor="c")
        c.showPage()
        c.save()
        return buf.getvalue()
