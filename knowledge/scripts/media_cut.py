"""
Keep only the first N seconds of a video.
If the video stream bitrate is above 20 Mb/s, re-encode video to ~15 Mb/s;
otherwise stream-copy (no re-encode for video).
On start copies the original to vault media-bak/, then replaces the source file.

Usage: python scripts/media_cut.py path/to/video.mp4
        python scripts/media_cut.py clip.mov -s 10
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

# Decimal megabits per second → bits per second
HIGH_BITRATE_BPS = 20_000_000
TARGET_VIDEO_BPS = 15_000_000


def vault_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _ffprobe_single_value(args_suffix: list[str], path: Path) -> str | None:
    if shutil.which("ffprobe") is None:
        return None
    cmd = [
        "ffprobe",
        "-v",
        "error",
        *args_suffix,
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return None
    s = (r.stdout or "").strip()
    if not s or s.upper() == "N/A":
        return None
    return s


def probe_video_bitrate_bps(path: Path) -> int | None:
    """Best-effort video stream bit_rate from ffprobe (bits/s). None if unknown."""
    raw = _ffprobe_single_value(
        ["-select_streams", "v:0", "-show_entries", "stream=bit_rate"],
        path,
    )
    if raw is not None:
        try:
            return int(raw)
        except ValueError:
            pass
    return None


def needs_transcode(bitrate_bps: int | None) -> bool:
    if bitrate_bps is None:
        return False
    return bitrate_bps > HIGH_BITRATE_BPS


def build_ffmpeg_cmd(
    src: Path,
    tmp: Path,
    seconds: float,
    transcode: bool,
) -> list[str]:
    ext = src.suffix.lower()
    base = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(src),
        "-t",
        str(seconds),
        "-map",
        "0",
        "-avoid_negative_ts",
        "make_zero",
    ]

    if not transcode:
        return [
            *base,
            "-c",
            "copy",
            str(tmp),
        ]

    # High bitrate: target ~15 Mb/s video
    if ext == ".webm":
        return [
            *base,
            "-c:v",
            "libvpx-vp9",
            "-b:v",
            f"{TARGET_VIDEO_BPS}",
            "-maxrate",
            f"{TARGET_VIDEO_BPS}",
            "-bufsize",
            f"{TARGET_VIDEO_BPS * 2}",
            "-c:a",
            "libopus",
            "-b:a",
            "128k",
            str(tmp),
        ]

    # mp4, mov, mkv, m4v, avi, …
    return [
        *base,
        "-c:v",
        "libx264",
        "-b:v",
        f"{TARGET_VIDEO_BPS}",
        "-maxrate",
        f"{TARGET_VIDEO_BPS}",
        "-bufsize",
        f"{TARGET_VIDEO_BPS * 2}",
        "-preset",
        "medium",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(tmp),
    ]


def cut_video(vault_root: Path, src: Path, seconds: float) -> None:
    """
    Backup original under vault_root/media-bak/, then replace src with
    first `seconds` of video (transcode if bitrate > 20 Mb/s).
    Raises RuntimeError on failure.
    """
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found in PATH")

    src = src.resolve()
    if not src.is_file():
        raise RuntimeError(f"Not a file: {src}")
    if seconds <= 0:
        raise RuntimeError("--seconds must be positive")

    vault_root = vault_root.resolve()
    try:
        rel_under_vault = src.relative_to(vault_root)
    except ValueError:
        rel_under_vault = Path("_outside_vault") / src.name

    bak_root = vault_root / "media-bak"
    bak = bak_root / rel_under_vault
    bak.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, bak)
    print(f"Backup: {bak}")

    tmp = src.parent / f".{src.stem}.{uuid.uuid4().hex[:8]}.trim{src.suffix}"

    v_bps = probe_video_bitrate_bps(src)
    transcode = needs_transcode(v_bps)
    if transcode:
        assert v_bps is not None
        print(
            f"Video bitrate ~{v_bps / 1e6:.1f} Mb/s > 20 Mb/s; re-encoding to ~15 Mb/s",
        )
    else:
        if v_bps is not None:
            print(f"Video bitrate ~{v_bps / 1e6:.1f} Mb/s; stream-copy")
        else:
            print("Bitrate unknown; stream-copy")

    cmd = build_ffmpeg_cmd(src, tmp, seconds, transcode)
    r = subprocess.run(cmd)
    if r.returncode != 0:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"ffmpeg exited with {r.returncode}")

    try:
        os.replace(tmp, src)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise
    print(f"Replaced: {src}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Keep only the first N seconds. Backs up to media-bak/, replaces the file. "
            "If video bitrate > 20 Mb/s, re-encode video to ~15 Mb/s; else stream-copy."
        ),
    )
    parser.add_argument(
        "video",
        type=Path,
        help="Video file path or name",
    )
    parser.add_argument(
        "--seconds",
        "-s",
        type=float,
        default=5.0,
        metavar="N",
        help="Keep only this many seconds from the start (default: 5)",
    )
    args = parser.parse_args()

    src = args.video.expanduser().resolve()
    root = vault_root()
    try:
        cut_video(root, src, args.seconds)
    except RuntimeError as e:
        print(e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
