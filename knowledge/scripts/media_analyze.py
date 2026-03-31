"""
Scan vault for media files and write media.md with sizes and GitHub push hints.
"""
from __future__ import annotations

import argparse
import os
from collections import Counter
from pathlib import Path

# GitHub: warning ~50 MiB, hard block 100 MiB per file for normal Git push
WARN_BYTES = 50 * 1024 * 1024
BLOCK_BYTES = 100 * 1024 * 1024

DEFAULT_EXTENSIONS = frozenset({
    "jpg", "jpeg", "png", "gif", "webp", "svg", "bmp",
    "mp4", "mov", "webm", "mkv", "wav", "mp3",
})

SKIP_DIR_NAMES = frozenset({".git", "__pycache__", ".venv", "venv", "node_modules"})


def human_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KiB"
    if n < 1024 * 1024 * 1024:
        return f"{n / (1024 * 1024):.1f} MiB"
    return f"{n / (1024 * 1024 * 1024):.2f} GiB"


def github_status(size: int) -> tuple[str, str]:
    """Return (short category key for counting, Russian label for table)."""
    if size > BLOCK_BYTES:
        return (
            "lfs",
            "Нужен Git LFS или внешнее хранилище (>100 МБ)",
        )
    if size > WARN_BYTES:
        return (
            "warn",
            ">50 МБ",
        )
    return ("ok", "OK (<50 МБ)")


def collect_media(
    root: Path,
    extensions: frozenset[str],
    include_obsidian: bool,
    extra_skip_dirs: frozenset[str] | None = None,
) -> list[tuple[Path, int, str, str]]:
    """List of (absolute path, size, category, github_label)."""
    skip_dirs = SKIP_DIR_NAMES | (extra_skip_dirs or frozenset())
    out: list[tuple[Path, int, str, str]] = []
    root = root.resolve()

    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        pruned: list[str] = []
        for d in dirnames:
            if d in skip_dirs:
                continue
            if not include_obsidian and d == ".obsidian":
                continue
            pruned.append(d)
        dirnames[:] = pruned

        base = Path(dirpath)
        for name in filenames:
            ext = Path(name).suffix.lower().lstrip(".")
            if ext not in extensions:
                continue
            p = base / name
            try:
                if not p.is_file():
                    continue
                size = p.stat().st_size
            except OSError:
                continue
            cat, label = github_status(size)
            out.append((p, size, cat, label))

    out.sort(key=lambda t: t[1], reverse=True)
    return out


def write_media_md(
    root: Path,
    rows: list[tuple[Path, int, str, str]],
    out_path: Path,
) -> None:
    root = root.resolve()
    total = sum(r[1] for r in rows)
    counts = Counter(r[2] for r in rows)

    lines = [
        "# Медиафайлы vault",
        "",
        "Сгенерировано скриптом `scripts/media_analyze.py`. "
        "Лимиты: GitHub рекомендует <50 МБ на файл; push блокируется свыше 100 МБ без LFS.",
        "",
        "| Имя файла | Размер | GitHub |",
        "| --- | --- | --- |",
    ]

    for p, size, _cat, label in rows:
        rel = p.relative_to(root).as_posix()
        # Pipe breaks markdown tables; Obsidian wikilinks use | for alias — avoid in path
        link_target = rel.replace("|", "_")
        safe_label = label.replace("|", "\\|")
        lines.append(
            f"| [[{link_target}]] | {human_size(size)} | {safe_label} |",
        )

    lines.extend(
        [
            "",
            "## Сводка",
            "",
            f"- **Файлов:** {len(rows)}",
            f"- **Суммарный размер:** {human_size(total)} ({total:,} байт)".replace(",", " "),
            f"- **OK (<50 МБ):** {counts.get('ok', 0)}",
            f"- **(>50 МБ):** {counts.get('warn', 0)}",
            f"- **>100 МБ (LFS / внешнее):** {counts.get('lfs', 0)}",
            "",
        ]
    )

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    default_root = script_dir.parent

    parser = argparse.ArgumentParser(
        description="Собрать медиафайлы и записать media.md с размерами и статусом для GitHub.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=default_root,
        help=f"Корень сканирования (по умолчанию: {default_root})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Куда записать media.md (по умолчанию: <root>/media.md)",
    )
    parser.add_argument(
        "--include-obsidian",
        action="store_true",
        help="Включать каталог .obsidian в обход",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    if not root.is_dir():
        raise SystemExit(f"Не каталог: {root}")

    out_path = args.output if args.output is not None else root / "media.md"

    rows = collect_media(root, DEFAULT_EXTENSIONS, args.include_obsidian)
    write_media_md(root, rows, out_path)
    print(f"Wrote {len(rows)} entries to {out_path}")


if __name__ == "__main__":
    main()
