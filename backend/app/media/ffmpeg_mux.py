"""FFmpeg helpers — mux narration, burn captions, optional music → final MP4."""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Optional

import httpx

from app.utils.logging import get_logger

logger = get_logger(__name__)


def resolve_ffmpeg(explicit: str = "") -> Optional[str]:
    if explicit and Path(explicit).exists():
        return explicit
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    # Common PATH name
    return "ffmpeg"


def narration_to_srt(text: str, duration_s: float = 30.0) -> str:
    """Build a simple timed SRT from narration when Whisper timings are unavailable."""
    words = (text or "").strip().split()
    if not words:
        return ""
    # Chunk into ~8-word caption lines
    chunks: list[str] = []
    cur: list[str] = []
    for w in words:
        cur.append(w)
        if len(cur) >= 8:
            chunks.append(" ".join(cur))
            cur = []
    if cur:
        chunks.append(" ".join(cur))
    slot = max(duration_s / max(len(chunks), 1), 1.2)
    lines: list[str] = []
    t = 0.0
    for i, chunk in enumerate(chunks, start=1):
        start = t
        end = min(duration_s, t + slot)
        lines.append(
            f"{i}\n{_ts(start)} --> {_ts(end)}\n{chunk}\n"
        )
        t = end
    return "\n".join(lines)


def _ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, milli = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{milli:03d}"


async def download_file(url: str, dest: Path) -> None:
    async with httpx.AsyncClient(timeout=180.0, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        dest.write_bytes(resp.content)


async def mux_commercial(
    *,
    video_url: str,
    audio_url: Optional[str],
    narration_text: str,
    ffmpeg_bin: str = "",
    music_url: Optional[str] = None,
    duration_hint: float = 30.0,
) -> bytes:
    """
    Merge base AI video + Kokoro VO + burned-in captions (+ optional music bed).
    Returns final MP4 bytes. Falls back to original video bytes if ffmpeg fails.
    """
    ff = resolve_ffmpeg(ffmpeg_bin)
    if not ff:
        async with httpx.AsyncClient(timeout=180.0, follow_redirects=True) as client:
            return (await client.get(video_url)).content

    with tempfile.TemporaryDirectory(prefix="lucero_mux_") as tmp:
        tdir = Path(tmp)
        video_path = tdir / "base.mp4"
        audio_path = tdir / "vo.wav"
        music_path = tdir / "music.mp3"
        srt_path = tdir / "captions.srt"
        out_path = tdir / "final.mp4"

        await download_file(video_url, video_path)
        srt_path.write_text(
            narration_to_srt(narration_text, duration_hint), encoding="utf-8"
        )

        has_audio = False
        if audio_url:
            try:
                await download_file(audio_url, audio_path)
                has_audio = True
            except Exception as exc:
                logger.warning("vo_download_failed", error=str(exc))

        has_music = False
        if music_url:
            try:
                await download_file(music_url, music_path)
                has_music = True
            except Exception as exc:
                logger.warning("music_download_failed", error=str(exc))

        # Escape srt path for ffmpeg subtitles filter (Windows-safe-ish)
        srt_esc = str(srt_path).replace("\\", "/").replace(":", "\\:")

        # Build filter: burn captions; optionally mix audio
        vf = f"subtitles='{srt_esc}':force_style='FontSize=18,PrimaryColour=&H00FFFFFF&,Outline=2'"

        cmd: list[str] = [ff, "-y", "-i", str(video_path)]
        if has_audio:
            cmd += ["-i", str(audio_path)]
        if has_music:
            cmd += ["-i", str(music_path)]

        # Map streams
        if has_audio and has_music:
            # VO primary + quiet music bed
            cmd += [
                "-filter_complex",
                f"[0:v]{vf}[v];[1:a]volume=1.0[a1];[2:a]volume=0.18[a2];[a1][a2]amix=inputs=2:duration=first[a]",
                "-map",
                "[v]",
                "-map",
                "[a]",
            ]
        elif has_audio:
            cmd += [
                "-vf",
                vf,
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-shortest",
            ]
        else:
            cmd += ["-vf", vf, "-map", "0:v:0", "-an"]

        cmd += [
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(out_path),
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, err = await proc.communicate()
            if proc.returncode != 0 or not out_path.exists():
                logger.warning(
                    "ffmpeg_mux_failed",
                    code=proc.returncode,
                    err=(err or b"")[:800].decode("utf-8", errors="ignore"),
                )
                return video_path.read_bytes()
            return out_path.read_bytes()
        except Exception as exc:
            logger.warning("ffmpeg_exec_failed", error=str(exc))
            return video_path.read_bytes()
