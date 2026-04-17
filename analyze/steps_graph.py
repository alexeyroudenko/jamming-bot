#!/usr/bin/env python3
"""Build a 3D force layout from bot Urls (visited=1) and write vertex coordinates to PLY.

Requires: pip install -r requirements-graph.txt (in this directory).

Reads SQLite table Urls: edges src_url -> url for rows with visited=1.
Row order for limiting: ORDER BY id (stable; not crawl step order).

Output PLY: one vertex per loaded row — x,y,z from spring layout of ``url``,
``id`` / ``src_id`` (Urls row ids), ``nx,ny,nz`` unit vector toward the next
row's ``url`` position (0,0,0 for the last row or degenerate cases).
"""

from __future__ import annotations

import argparse
import math
import sqlite3
import sys
from pathlib import Path

import networkx as nx

DEFAULT_DB = Path(__file__).resolve().parent.parent / "bot-service" / "bot" / "database.db"
DEFAULT_OUT = Path(__file__).resolve().parent / "steps_coords.ply"
DEFAULT_ROW_LIMIT = 1000
DEFAULT_ITERATIONS = 50


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Load visited=1 rows from bot Urls SQLite, build a directed graph "
            "(src_url -> url), run 3D spring layout, write ASCII PLY vertices."
        )
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help=f"Path to bot SQLite database, default: {DEFAULT_DB}",
    )
    lim = parser.add_mutually_exclusive_group()
    lim.add_argument(
        "--all",
        action="store_true",
        help="Use all rows with visited=1 (can be slow and memory-heavy).",
    )
    lim.add_argument(
        "--steps",
        type=int,
        metavar="N",
        default=None,
        help=f"Max number of rows to load (default without --all: {DEFAULT_ROW_LIMIT}).",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=DEFAULT_ITERATIONS,
        help=f"Spring layout iterations, default: {DEFAULT_ITERATIONS}.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output PLY path, default: {DEFAULT_OUT}",
    )
    return parser.parse_args()


def row_limit_from_args(args: argparse.Namespace) -> int | None:
    if args.all:
        return None
    if args.steps is not None:
        if args.steps < 1:
            print("error: --steps must be >= 1", file=sys.stderr)
            sys.exit(2)
        return args.steps
    return DEFAULT_ROW_LIMIT


def load_rows(db_path: Path, limit: int | None) -> list[tuple[int, str, str | None]]:
    if not db_path.is_file():
        print(f"error: database not found: {db_path}", file=sys.stderr)
        sys.exit(1)
    sql = (
        "SELECT id, url, src_url FROM Urls WHERE visited = 1 ORDER BY id"
        + (" LIMIT ?" if limit is not None else "")
    )
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        if limit is not None:
            cur.execute(sql, (limit,))
        else:
            cur.execute(sql)
        raw_rows = cur.fetchall()
    finally:
        conn.close()

    out: list[tuple[int, str, str | None]] = []
    for row_id, url, src_url in raw_rows:
        if url is None:
            continue
        u = str(url).strip()
        if not u:
            continue
        s = str(src_url).strip() if src_url is not None else ""
        out.append((int(row_id), u, s if s else None))
    return out


def build_graph(rows: list[tuple[int, str, str | None]]) -> nx.DiGraph:
    g: nx.DiGraph = nx.DiGraph()
    for _row_id, url, src in rows:
        if src:
            g.add_edge(src, url)
        else:
            g.add_node(url)
    return g


def layout_3d(g: nx.DiGraph, iterations: int) -> dict:
    if g.number_of_nodes() == 0:
        return {}
    return nx.spring_layout(g, dim=3, seed=42, iterations=iterations)


def _first_id_by_url(rows: list[tuple[int, str, str | None]]) -> dict[str, int]:
    """Smallest id in the loaded window for each url (ORDER BY id list)."""
    first: dict[str, int] = {}
    for row_id, url, _src in rows:
        if url not in first:
            first[url] = row_id
    return first


def _resolve_src_id(
    conn: sqlite3.Connection,
    src_url: str,
    cache: dict[str, int],
    window_first_id: dict[str, int],
) -> int:
    if src_url in cache:
        return cache[src_url]
    if src_url in window_first_id:
        sid = window_first_id[src_url]
        cache[src_url] = sid
        return sid
    cur = conn.cursor()
    cur.execute(
        "SELECT MIN(id) FROM Urls WHERE visited = 1 AND url = ?",
        (src_url,),
    )
    row = cur.fetchone()
    if row and row[0] is not None:
        sid = int(row[0])
    else:
        sid = -1
    cache[src_url] = sid
    return sid


def _direction_to_next(
    pos_a: tuple[float, float, float],
    pos_b: tuple[float, float, float],
    eps: float = 1e-12,
) -> tuple[float, float, float]:
    dx = pos_b[0] - pos_a[0]
    dy = pos_b[1] - pos_a[1]
    dz = pos_b[2] - pos_a[2]
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    if length < eps:
        return (0.0, 0.0, 0.0)
    inv = 1.0 / length
    return (dx * inv, dy * inv, dz * inv)


def _pos_tuple(positions: dict, url: str) -> tuple[float, float, float]:
    pos = positions.get(url)
    if pos is None:
        return (0.0, 0.0, 0.0)
    return (float(pos[0]), float(pos[1]), float(pos[2]))


def write_ply_ascii(
    path: Path,
    rows: list[tuple[int, str, str | None]],
    positions: dict,
    src_ids: list[int],
    normals: list[tuple[float, float, float]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = len(rows)
    lines = [
        "ply",
        "format ascii 1.0",
        "comment steps_graph.py: Urls visited=1 row order ORDER BY id",
        f"element vertex {n}",
        "property float x",
        "property float y",
        "property float z",
        "property int id",
        "property int src_id",
        "property float nx",
        "property float ny",
        "property float nz",
        "end_header",
    ]
    for (row_id, url, _src), sid, (nx, ny, nz) in zip(
        rows, src_ids, normals, strict=True
    ):
        x, y, z = _pos_tuple(positions, url)
        lines.append(f"{x} {y} {z} {row_id} {sid} {nx} {ny} {nz}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    limit = row_limit_from_args(args)
    rows = load_rows(args.db, limit)
    g = build_graph(rows)
    pos = layout_3d(g, args.iterations)

    window_first = _first_id_by_url(rows)
    src_id_cache: dict[str, int] = {}
    src_ids: list[int] = []
    conn = sqlite3.connect(str(args.db))
    try:
        for _rid, _url, src in rows:
            if not src:
                src_ids.append(-1)
            else:
                src_ids.append(_resolve_src_id(conn, src, src_id_cache, window_first))
    finally:
        conn.close()

    normals: list[tuple[float, float, float]] = []
    for i, (_row_id, url, _src) in enumerate(rows):
        p_cur = _pos_tuple(pos, url)
        if i + 1 < len(rows):
            _next_id, next_url, _ns = rows[i + 1]
            p_next = _pos_tuple(pos, next_url)
            normals.append(_direction_to_next(p_cur, p_next))
        else:
            normals.append((0.0, 0.0, 0.0))

    write_ply_ascii(args.output, rows, pos, src_ids, normals)

    mode = "all rows" if limit is None else f"up to {limit} rows"
    print(
        f"Loaded ({mode}): {len(rows)} Urls rows -> "
        f"graph |V|={g.number_of_nodes()} |E|={g.number_of_edges()}, "
        f"layout iterations={args.iterations}, wrote {args.output} "
        f"({len(rows)} vertices with id, src_id, nx ny nz)"
    )


if __name__ == "__main__":
    main()
