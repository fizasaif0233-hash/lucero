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


def _draw_premium_seal(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    r: int,
    *,
    accent: Tuple[int, int, int],
) -> None:
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=accent, width=max(3, r // 16))
    draw.ellipse(
        (cx - int(r * 0.82), cy - int(r * 0.82), cx + int(r * 0.82), cy + int(r * 0.82)),
        outline=accent,
        width=max(2, r // 22),
    )
    title = _font(max(14, r // 5), bold=True)
    small = _font(max(12, r // 6), bold=False)
    for i, line in enumerate(("PREMIUM", "QUALITY", "100% AGAVE")):
        font = title if i < 2 else small
        tw = draw.textlength(line, font=font)
        draw.text((cx - tw / 2, cy - r * 0.35 + i * (r * 0.28)), line, fill=accent, font=font)


def _draw_feature_icon(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    size: int,
    kind: int,
    *,
    accent: Tuple[int, int, int],
) -> None:
    s = size
    if kind % 5 == 0:
        draw.ellipse((x, y, x + s, y + s), outline=accent, width=max(2, s // 12))
        draw.ellipse((x + s // 4, y + s // 4, x + 3 * s // 4, y + 3 * s // 4), fill=accent)
    elif kind % 5 == 1:
        pts = [
            (x + s // 2, y),
            (x + s, y + s // 4),
            (x + s, y + 2 * s // 3),
            (x + s // 2, y + s),
            (x, y + 2 * s // 3),
            (x, y + s // 4),
        ]
        draw.polygon(pts, outline=accent)
    elif kind % 5 == 2:
        pts = [
            (x + s // 2, y),
            (x + s, y + s // 2),
            (x + s // 2, y + s),
            (x, y + s // 2),
        ]
        draw.polygon(pts, outline=accent)
    elif kind % 5 == 3:
        draw.ellipse((x + s // 8, y + s // 8, x + s // 2, y + s // 2), outline=accent, width=max(2, s // 14))
        draw.ellipse((x + s // 2, y + s // 8, x + 7 * s // 8, y + s // 2), outline=accent, width=max(2, s // 14))
        draw.ellipse((x + s // 3, y + s // 2, x + 2 * s // 3, y + 7 * s // 8), outline=accent, width=max(2, s // 14))
    else:
        draw.ellipse((x + s // 4, y, x + 3 * s // 4, y + s // 2), outline=accent, width=max(2, s // 12))
        draw.polygon(
            [(x + s // 2, y + s), (x + s // 4, y + s // 2), (x + 3 * s // 4, y + s // 2)],
            fill=accent,
        )


def _split_feature(feat: str) -> Tuple[str, str]:
    if "|" in feat:
        left, right = feat.split("|", 1)
        return left.strip(), right.strip()
    if " — " in feat:
        left, right = feat.split(" — ", 1)
        return left.strip(), right.strip()
    return feat.strip(), ""


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
        """Cinematic flyer: landscape + bottle right, copy left (reference ad style)."""
        w, h = size
        s = w / 2480.0
        accent = GOLD
        text_main = CREAM
        muted = SOFT_GOLD

        if product_url:
            try:
                src = await _fetch_image(product_url)
                img = _fit_cover(src, (w, h))
            except Exception:
                img = Image.new("RGB", (w, h), BLACK if theme == "black_gold" else GREEN)
        else:
            img = Image.new("RGB", (w, h), BLACK if theme == "black_gold" else GREEN)
            glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow)
            for i, alpha in enumerate((50, 28, 14)):
                pad = int(w * (0.1 + i * 0.08))
                gd.ellipse(
                    (pad, int(h * 0.15), w - pad // 2, int(h * 0.75)),
                    fill=(201, 162, 39, alpha),
                )
            img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")

        # Left readable panel + bottom fade
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        for i in range(int(w * 0.62)):
            t = 1.0 - (i / (w * 0.62))
            alpha = int(210 * (t**1.15))
            od.line([(i, 0), (i, h)], fill=(4, 8, 18, alpha))
        od.rectangle((0, int(h * 0.78), w, h), fill=(0, 0, 0, 140))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img)

        border = max(4, int(10 * s))
        inset = int(70 * s)
        draw.rectangle((inset, inset, w - inset, h - inset), outline=accent, width=border)
        draw.rectangle(
            (
                inset + border * 2,
                inset + border * 2,
                w - inset - border * 2,
                h - inset - border * 2,
            ),
            outline=SOFT_GOLD,
            width=max(1, border // 2),
        )
        tick = int(70 * s)
        for cx, cy in (
            (inset, inset),
            (w - inset, inset),
            (inset, h - inset),
            (w - inset, h - inset),
        ):
            draw.line((cx - tick // 2, cy, cx + tick // 2, cy), fill=accent, width=border)
            draw.line((cx, cy - tick // 2, cx, cy + tick // 2), fill=accent, width=border)

        left_w = int(w * 0.52)
        margin = int(150 * s)
        col_w = left_w - margin

        y = int(160 * s)
        brand_font = _font(int(72 * s), bold=True)
        script_font = _font(int(54 * s), bold=False)
        small_font = _font(int(28 * s), bold=True)
        _draw_logo_mark(
            draw,
            (w // 2 - int(70 * s), y),
            int(140 * s),
            accent=accent,
            fill=text_main,
        )
        y += int(155 * s)
        title_line = "BLUE PRINCE 21"
        tw = draw.textlength(title_line, font=brand_font)
        draw.text(((w - tw) / 2, y), title_line, fill=accent, font=brand_font)
        y += int(78 * s)
        script = "McKinzy"
        tw = draw.textlength(script, font=script_font)
        draw.text(((w - tw) / 2, y), script, fill=SOFT_GOLD, font=script_font)
        y += int(58 * s)
        prem = "PREMIUM TEQUILA"
        tw = draw.textlength(prem, font=small_font)
        draw.text(((w - tw) / 2, y), prem, fill=text_main, font=small_font)

        _draw_premium_seal(draw, w - int(280 * s), int(280 * s), int(150 * s), accent=accent)

        y = int(520 * s)
        head_font = _font(int(68 * s), bold=True)
        tag_font = _font(int(36 * s), bold=True)
        body_font = _font(int(32 * s), bold=False)
        feat_title = _font(int(30 * s), bold=True)
        feat_sub = _font(int(26 * s), bold=False)

        headline = (copy.get("headline") or "EXPERIENCE TRUE PREMIUM TEQUILA").upper()
        for line in _wrap(draw, headline, head_font, col_w)[:4]:
            draw.text((margin, y), line, fill=text_main, font=head_font)
            y += int(72 * s)

        y += int(18 * s)
        tagline = (
            copy.get("tagline") or copy.get("subhead") or "DRINK IT. TRADE IT. OWN IT."
        ).upper()
        draw.text((margin, y), tagline, fill=accent, font=tag_font)
        y += int(56 * s)

        body = copy.get("body") or (
            "Blue Prince 21 McKinzy is more than tequila. It's a movement. "
            "Crafted for those who appreciate quality, authenticity, and legacy."
        )
        for line in _wrap(draw, body, body_font, col_w)[:5]:
            draw.text((margin, y), line, fill=muted, font=body_font)
            y += int(38 * s)

        y += int(36 * s)
        features = _parse_features(copy)[:5]
        icon_s = int(48 * s)
        for i, feat in enumerate(features):
            title_f, detail = _split_feature(feat)
            _draw_feature_icon(draw, margin, y, icon_s, i, accent=accent)
            tx = margin + icon_s + int(24 * s)
            draw.text((tx, y), title_f.upper(), fill=accent, font=feat_title)
            if detail:
                draw.text((tx, y + int(34 * s)), detail, fill=text_main, font=feat_sub)
                y += int(78 * s)
            else:
                y += int(62 * s)

        website = (copy.get("website") or PRIMARY_WEBSITE).strip()
        if website and not website.startswith("http"):
            website = "https://" + website.lstrip("/")
        site_display = website.replace("https://www.", "").replace("https://", "")

        footer_y = h - int(520 * s)
        qr_size = int(220 * s)
        qr = _make_qr(website, qr_size, dark=CHARCOAL, light=CREAM)
        qr_matte = Image.new(
            "RGB", (qr_size + int(20 * s), qr_size + int(20 * s)), accent
        )
        qr_matte.paste(qr, (int(10 * s), int(10 * s)))
        img.paste(qr_matte, (margin, footer_y))

        info_x = margin + qr_matte.size[0] + int(36 * s)
        info_font = _font(int(30 * s), bold=True)
        tiny = _font(int(26 * s), bold=False)
        draw.text((info_x, footer_y + int(20 * s)), "JOIN THE MOVEMENT", fill=accent, font=info_font)
        draw.text((info_x, footer_y + int(60 * s)), "SCAN TO DISCOVER MORE", fill=text_main, font=tiny)
        draw.text((info_x, footer_y + int(110 * s)), "VISIT OUR WEBSITE", fill=accent, font=info_font)
        draw.text((info_x, footer_y + int(150 * s)), site_display, fill=text_main, font=tiny)
        draw.text((info_x, footer_y + int(200 * s)), "@blueprince21mckinzy", fill=muted, font=tiny)

        cta = (copy.get("cta") or "ORDER NOW").upper()
        cta_font = _font(int(40 * s), bold=True)
        btn_w = int(420 * s)
        btn_h = int(90 * s)
        btn_x = margin
        btn_y = h - int(220 * s)
        draw.rectangle((btn_x, btn_y, btn_x + btn_w, btn_y + btn_h), fill=accent)
        draw.rectangle(
            (
                btn_x + int(6 * s),
                btn_y + int(6 * s),
                btn_x + btn_w - int(6 * s),
                btn_y + btn_h - int(6 * s),
            ),
            outline=CHARCOAL,
            width=max(2, int(3 * s)),
        )
        tw = draw.textlength(cta, font=cta_font)
        draw.text(
            (btn_x + (btn_w - tw) / 2, btn_y + (btn_h - int(40 * s)) / 2),
            cta,
            fill=CHARCOAL,
            font=cta_font,
        )

        draw.text(
            (w - margin - int(700 * s), h - int(150 * s)),
            "DRINK RESPONSIBLY. CELEBRATE LEGACY.",
            fill=muted,
            font=_font(int(24 * s), bold=True),
        )
        draw.text(
            (w // 2 - int(200 * s), h - int(110 * s)),
            "A.W. McKinzy  ·  FOUNDER & VISIONARY",
            fill=SOFT_GOLD,
            font=_font(int(22 * s), bold=False),
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
