"""
Walk the vault:
- Videos > 5 MiB: media_cut (backup to media-bak/, trim, transcode if high bitrate).
- Raster images > 500 KiB: backup to media-backup/, shrink via ffmpeg (scale + quality),
  optional WebP fallback; overwrite only if output is smaller than original.
Then write media.md like media_analyze.py (skips media-bak/ and media-backup/).

Usage: python scripts/media_organize.py
       python scripts/media_organize.py --seconds 5 --root .
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import media_analyze  # noqa: E402
import media_cut  # noqa: E402

VIDEO_EXTENSIONS = frozenset({"mp4", "mov", "webm", "mkv"})
IMAGE_EXTENSIONS = frozenset({"jpg", "jpeg", "png", "gif", "webp", "bmp"})
EXTRA_SKIP_DIRS = frozenset({"media-bak", "media-backup"})
MIN_VIDEO_BYTES = 5 * 1024 * 1024
DEFAULT_IMAGE_MAX_BYTES = 500 * 1024

_JPEG_ATTEMPTS: list[tuple[int, int]] = [
    (4096, 8),
    (2560, 11),
    (1920, 14),
    (1600, 17),
    (1280, 20),
    (1024, 24),
    (800, 28),
]

_PNG_EDGES: list[int] = [4096, 2560, 1920, 1600, 1280, 1024, 800]

_WEBP_ATTEMPTS: list[tuple[int, int]] = [
    (4096, 88),
    (2560, 82),
    (1920, 78),
    (1600, 74),
    (1280, 70),
    (1024, 65),
    (800, 60),
]

_GIF_EDGES: list[int] = [2048, 1600, 1280, 1024, 800]


def _scale_vf(max_edge: int) -> str:
    return (
        f"scale=w='min({max_edge},iw)':h='min({max_edge},ih)':"
        f"force_original_aspect_ratio=decrease"
    )


def _backup_under(vault_root: Path, src: Path, backup_root_name: str) -> Path:
    vault_root = vault_root.resolve()
    src = src.resolve()
    try:
        rel = src.relative_to(vault_root)
    except ValueError:
        rel = Path("_outside_vault") / src.name
    dest = vault_root / backup_root_name / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return dest


def _run_ffmpeg(args: list[str]) -> bool:
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode == 0


def _build_image_cmd(
    src: Path,
    tmp: Path,
    kind: str,
    max_edge: int,
    *,
    jpeg_q: int | None = None,
    webp_q: int | None = None,
    to_webp: bool = False,
) -> list[str]:
    vf = _scale_vf(max_edge)
    base = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(src),
        "-vf",
        vf,
    ]
    if to_webp:
        return [
            *base,
            "-c:v",
            "libwebp",
            "-quality",
            str(webp_q or 75),
            str(tmp),
        ]
    if kind in ("jpg", "jpeg"):
        return [*base, "-q:v", str(jpeg_q or 12), str(tmp)]
    if kind == "png":
        return [
            *base,
            "-c:v",
            "png",
            "-compression_level",
            "9",
            str(tmp),
        ]
    if kind == "webp":
        return [
            *base,
            "-c:v",
            "libwebp",
            "-quality",
            str(webp_q or 78),
            str(tmp),
        ]
    if kind == "gif":
        return [*base, "-c:v", "gif", str(tmp)]
    if kind == "bmp":
        return [*base, "-q:v", str(jpeg_q or 12), str(tmp)]
    return [*base, "-q:v", str(jpeg_q or 12), str(tmp)]


def _kind_from_suffix(ext: str) -> str:
    e = ext.lower().lstrip(".")
    return "jpeg" if e == "jpg" else e


def optimize_image(vault_root: Path, src: Path, max_bytes: int) -> None:
    """
    Copy to media-backup/, then ffmpeg passes; replace only if smaller than original.
    BMP may become .jpg; other types may fall back to .webp if still large.
    """
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found in PATH")

    vault_root = vault_root.resolve()
    src = src.resolve()
    if not src.is_file():
        raise RuntimeError(f"Not a file: {src}")

    ext = src.suffix.lower()
    if not ext:
        raise RuntimeError(f"No extension: {src}")

    bak = _backup_under(vault_root, src, "media-backup")
    print(f"Image backup: {bak}")

    orig_size = src.stat().st_size
    uid = uuid.uuid4().hex[:8]
    work_dir = src.parent
    stem = src.stem

    best_tmp: Path | None = None
    best_size = orig_size
    best_dest: Path = src

    def consider(tmp_path: Path, dest_path: Path) -> None:
        nonlocal best_tmp, best_size, best_dest
        if not tmp_path.is_file():
            return
        sz = tmp_path.stat().st_size
        if sz < best_size:
            if best_tmp is not None and best_tmp.exists() and best_tmp != tmp_path:
                best_tmp.unlink(missing_ok=True)
            best_tmp = tmp_path
            best_size = sz
            best_dest = dest_path

    def cleanup_uid_globs() -> None:
        for p in work_dir.glob(f".{stem}.{uid}.*"):
            if best_tmp is None or p.resolve() != best_tmp.resolve():
                p.unlink(missing_ok=True)

    kind = _kind_from_suffix(ext)

    if ext == ".bmp":
        for max_edge, jq in _JPEG_ATTEMPTS:
            t = work_dir / f".{stem}.{uid}.bmp-{max_edge}.jpg"
            cmd = _build_image_cmd(src, t, "bmp", max_edge, jpeg_q=jq)
            if _run_ffmpeg(cmd):
                consider(t, src.with_suffix(".jpg"))
                if best_size <= max_bytes:
                    break
            t.unlink(missing_ok=True)
    elif ext in (".jpg", ".jpeg"):
        for max_edge, jq in _JPEG_ATTEMPTS:
            t = work_dir / f".{stem}.{uid}.opt{ext}"
            cmd = _build_image_cmd(src, t, "jpeg", max_edge, jpeg_q=jq)
            if _run_ffmpeg(cmd):
                consider(t, src)
                if best_size <= max_bytes:
                    break
            t.unlink(missing_ok=True)
    elif ext == ".png":
        for max_edge in _PNG_EDGES:
            t = work_dir / f".{stem}.{uid}.opt.png"
            cmd = _build_image_cmd(src, t, "png", max_edge)
            if _run_ffmpeg(cmd):
                consider(t, src)
                if best_size <= max_bytes:
                    break
            t.unlink(missing_ok=True)
    elif ext == ".webp":
        for max_edge, wq in _WEBP_ATTEMPTS:
            t = work_dir / f".{stem}.{uid}.opt.webp"
            cmd = _build_image_cmd(src, t, "webp", max_edge, webp_q=wq)
            if _run_ffmpeg(cmd):
                consider(t, src)
                if best_size <= max_bytes:
                    break
            t.unlink(missing_ok=True)
    elif ext == ".gif":
        for max_edge in _GIF_EDGES:
            t = work_dir / f".{stem}.{uid}.opt.gif"
            cmd = _build_image_cmd(src, t, "gif", max_edge)
            if _run_ffmpeg(cmd):
                consider(t, src)
                if best_size <= max_bytes:
                    break
            t.unlink(missing_ok=True)

    # WebP fallback when still above target or no in-format win
    need_webp = best_size > max_bytes or best_size >= orig_size
    if need_webp and ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"):
        for max_edge, wq in _WEBP_ATTEMPTS:
            t = work_dir / f".{stem}.{uid}.fb.webp"
            cmd = _build_image_cmd(
                src, t, kind, max_edge, to_webp=True, webp_q=wq,
            )
            if _run_ffmpeg(cmd):
                consider(t, src.with_suffix(".webp"))
                if best_size <= max_bytes:
                    break
            t.unlink(missing_ok=True)

    if best_tmp is None or best_size >= orig_size:
        cleanup_uid_globs()
        print(f"No smaller image output; left unchanged: {src}")
        return

    dest = best_dest.resolve()
    src_r = src.resolve()
    if dest == src_r:
        os.replace(best_tmp, src)
        print(f"Replaced: {src} ({orig_size} → {best_size} B)")
    else:
        if src_r.exists():
            src.unlink()
        os.replace(best_tmp, dest)
        print(f"Replaced: {src_r} → {dest} ({orig_size} → {best_size} B)")

    cleanup_uid_globs()


def main() -> None:
    default_root = SCRIPT_DIR.parent
    parser = argparse.ArgumentParser(
        description=(
            "Videos > threshold: media_cut. Images > 500 KiB (configurable): optimize. "
            "Then regenerate media.md."
        ),
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=default_root,
        help=f"Vault root (default: {default_root})",
    )
    parser.add_argument(
        "--seconds",
        "-s",
        type=float,
        default=5.0,
        metavar="N",
        help="Keep only this many seconds when cutting video (default: 5)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="media.md path (default: <root>/media.md)",
    )
    parser.add_argument(
        "--include-obsidian",
        action="store_true",
        help="Include .obsidian when scanning",
    )
    parser.add_argument(
        "--min-mib",
        type=float,
        default=5.0,
        metavar="N",
        help="Only process videos larger than N MiB (default: 5)",
    )
    parser.add_argument(
        "--image-max-kib",
        type=float,
        default=500.0,
        metavar="N",
        help="Optimize images larger than N KiB (default: 500)",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    if not root.is_dir():
        raise SystemExit(f"Not a directory: {root}")

    if args.seconds <= 0:
        raise SystemExit("--seconds must be positive")

    min_video_bytes = int(args.min_mib * 1024 * 1024)
    image_min_bytes = int(args.image_max_kib * 1024)

    video_rows = media_analyze.collect_media(
        root,
        VIDEO_EXTENSIONS,
        args.include_obsidian,
        EXTRA_SKIP_DIRS,
    )
    to_cut = [(p, sz) for p, sz, _, _ in video_rows if sz > min_video_bytes]
    to_cut.sort(key=lambda t: t[1], reverse=True)

    print(f"Videos found: {len(video_rows)}; over {args.min_mib:g} MiB: {len(to_cut)}")

    errors = 0
    for path, sz in to_cut:
        rel = path.relative_to(root)
        print(f"\n--- video {rel} ({sz / (1024 * 1024):.1f} MiB) ---")
        try:
            media_cut.cut_video(root, path, args.seconds)
        except RuntimeError as e:
            print(e, file=sys.stderr)
            errors += 1
        except OSError as e:
            print(e, file=sys.stderr)
            errors += 1

    image_rows = media_analyze.collect_media(
        root,
        IMAGE_EXTENSIONS,
        args.include_obsidian,
        EXTRA_SKIP_DIRS,
    )
    to_img = [(p, sz) for p, sz, _, _ in image_rows if sz > image_min_bytes]
    to_img.sort(key=lambda t: t[1], reverse=True)

    print(
        f"\nImages found: {len(image_rows)}; over {args.image_max_kib:g} KiB: {len(to_img)}",
    )

    for path, sz in to_img:
        rel = path.relative_to(root)
        print(f"\n--- image {rel} ({sz / 1024:.1f} KiB) ---")
        try:
            optimize_image(root, path, image_min_bytes)
        except RuntimeError as e:
            print(e, file=sys.stderr)
            errors += 1
        except OSError as e:
            print(e, file=sys.stderr)
            errors += 1

    out_path = args.output if args.output is not None else root / "media.md"
    all_rows = media_analyze.collect_media(
        root,
        media_analyze.DEFAULT_EXTENSIONS,
        args.include_obsidian,
        EXTRA_SKIP_DIRS,
    )
    media_analyze.write_media_md(root, all_rows, out_path)
    print(f"\nWrote {len(all_rows)} entries to {out_path}")
    if errors:
        print(f"Completed with {errors} error(s).", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
