#!/usr/bin/env python3
import argparse
import csv
import hashlib
import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


DEFAULT_TAGS_API_URL = os.getenv(
    "EMBED_TAGS_API_URL",
    "https://jamming-bot.arthew0.online/api/tags/get/",
)
DEFAULT_EMBEDDINGS_API_URL = os.getenv(
    "EMBED_TAGS_EMBEDDINGS_API_URL",
    "https://jamming-bot.arthew0.online/api/tags/embeddings/",
)
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "out" / "embed_tags"
DEFAULT_PAGE_SIZE = 500
DEFAULT_BATCH_SIZE = 80
DEFAULT_USER_AGENT = "embed-tags-mvp/1.0"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Export aggregated tags with 3D embedding coordinates."
    )
    parser.add_argument(
        "--tags-api-url",
        default=DEFAULT_TAGS_API_URL,
        help="Aggregated tags API endpoint, default: %(default)s",
    )
    parser.add_argument(
        "--embeddings-api-url",
        default=DEFAULT_EMBEDDINGS_API_URL,
        help="Embeddings API endpoint, default: %(default)s",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for analysis artifacts, default: %(default)s",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=DEFAULT_PAGE_SIZE,
        help="How many tags to request per page from tags API, default: %(default)s",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="How many words to send per embeddings request, default: %(default)s",
    )
    parser.add_argument(
        "--max-tags",
        type=int,
        default=0,
        help="Optional hard cap on exported tags, default: all",
    )
    parser.add_argument(
        "--projection",
        choices=("api3d", "api3d_alt", "api2d_z"),
        default="api3d",
        help="3D coordinate source, default: %(default)s",
    )
    parser.add_argument(
        "--min-count",
        type=int,
        default=1,
        help="Skip tags with count below this threshold, default: %(default)s",
    )
    parser.add_argument(
        "--min-sim",
        type=float,
        default=0.38,
        help="Forwarded to embeddings API for links, default: %(default)s",
    )
    parser.add_argument(
        "--max-links",
        type=int,
        default=160,
        help="Forwarded to embeddings API for similarity links, default: %(default)s",
    )
    return parser.parse_args()


def fetch_json(url, params=None, payload=None):
    full_url = url
    body = None
    headers = {
        "Accept": "application/json",
        "User-Agent": DEFAULT_USER_AGENT,
    }
    if params:
        query = urllib.parse.urlencode(params)
        delimiter = "&" if "?" in url else "?"
        full_url = f"{url}{delimiter}{query}"
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(full_url, data=body, headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_all_tags(tags_api_url, page_size, max_tags, min_count):
    tags = []
    page = 0
    while True:
        payload = fetch_json(tags_api_url, params={"count": page_size, "page": page})
        if not isinstance(payload, list):
            raise ValueError("Tags API must return a list")
        rows = normalize_tag_rows(payload, min_count=min_count)
        if not rows:
            break
        tags.extend(rows)
        if len(payload) < page_size:
            break
        if max_tags and len(tags) >= max_tags:
            tags = tags[:max_tags]
            break
        page += 1
    if not tags:
        raise ValueError("No tags returned by API")
    return tags


def normalize_tag_rows(rows, min_count):
    dedup = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        count = safe_int(row.get("count"), default=0)
        if count < min_count:
            continue
        key = name.casefold()
        current = dedup.get(key)
        if current is None or count > current["count"]:
            dedup[key] = {"name": name, "count": count}
    normalized = list(dedup.values())
    normalized.sort(key=lambda item: (-item["count"], item["name"].casefold()))
    return normalized


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def choose_projection_row(embedding_payload, row_idx, projection):
    if projection == "api3d":
        vectors = embedding_payload.get("vectors3d_current") or embedding_payload.get("vectors3d") or []
        return ensure_xyz(vectors, row_idx)
    if projection == "api3d_alt":
        vectors = embedding_payload.get("vectors3d_alt") or []
        return ensure_xyz(vectors, row_idx)
    vectors2d = embedding_payload.get("vectors2d_current") or embedding_payload.get("vectors2d") or []
    xy = ensure_xy(vectors2d, row_idx)
    return fallback_3d_from_2d(xy, seed=f"{embedding_payload['words'][row_idx]}:{row_idx}")


def ensure_xy(rows, row_idx):
    if row_idx >= len(rows):
        return [0.0, 0.0]
    row = rows[row_idx]
    if not isinstance(row, list) or len(row) < 2:
        return [0.0, 0.0]
    return [float(row[0]), float(row[1])]


def ensure_xyz(rows, row_idx):
    if row_idx >= len(rows):
        return [0.0, 0.0, 0.0]
    row = rows[row_idx]
    if not isinstance(row, list) or len(row) < 3:
        return [0.0, 0.0, 0.0]
    return [float(row[0]), float(row[1]), float(row[2])]


def fallback_3d_from_2d(xy, seed):
    x = float(xy[0]) if len(xy) > 0 else 0.0
    y = float(xy[1]) if len(xy) > 1 else 0.0
    phase = deterministic_float(seed)
    z = 0.55 * math.sin(x * 4.2 + y * 2.7 + phase * math.pi) * math.cos(
        x * 1.9 - y * 3.1 + phase * math.tau
    )
    return [x, y, z]


def deterministic_float(value):
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def fetch_embeddings(tags, embeddings_api_url, batch_size, projection, min_sim, max_links):
    points = []
    embedding_batches = []
    for offset in range(0, len(tags), batch_size):
        batch_tags = tags[offset : offset + batch_size]
        words = [item["name"] for item in batch_tags]
        payload = fetch_json(
            embeddings_api_url,
            payload={
                "words": words,
                "max_words": max(len(words), 4),
                "min_sim": min_sim,
                "max_links": max_links,
            },
        )
        batch_result = {
            "input_words": words,
            "response": payload,
            "projection": projection,
        }
        embedding_batches.append(batch_result)
        response_words = payload.get("words") or []
        for idx, word in enumerate(response_words):
            point = {
                "label": word,
                "count": lookup_count(batch_tags, word),
                "projection": projection,
                "mode": payload.get("mode", "unknown"),
                "coords": rounded_xyz(choose_projection_row(payload, idx, projection)),
            }
            points.append(point)
    if not points:
        raise ValueError("Embeddings API returned no usable points")
    return points, embedding_batches


def lookup_count(tags, word):
    key = word.casefold()
    for item in tags:
        if item["name"].casefold() == key:
            return item["count"]
    return 0


def rounded_xyz(coords):
    return [round(float(coords[0]), 6), round(float(coords[1]), 6), round(float(coords[2]), 6)]


def build_csv_rows(points):
    rows = []
    for idx, point in enumerate(points):
        x, y, z = point["coords"]
        rows.append(
            {
                "id": idx,
                "label": point["label"],
                "count": point["count"],
                "x": x,
                "y": y,
                "z": z,
                "projection": point["projection"],
                "mode": point["mode"],
            }
        )
    return rows


def write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path, rows):
    fieldnames = ["id", "label", "count", "x", "y", "z", "projection", "mode"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_ply(path, rows):
    header = [
        "ply",
        "format ascii 1.0",
        "comment generated_by embed_tags.py",
        "comment label_index maps to metadata.json labels_by_id",
        f"element vertex {len(rows)}",
        "property float x",
        "property float y",
        "property float z",
        "property int count",
        "property int label_index",
        "end_header",
    ]
    lines = []
    for row in rows:
        lines.append(
            f"{row['x']:.6f} {row['y']:.6f} {row['z']:.6f} {int(row['count'])} {int(row['id'])}"
        )
    path.write_text("\n".join(header + lines) + "\n", encoding="utf-8")


def build_metadata(args, tags, points, csv_rows, embedding_batches, output_paths):
    return {
        "source": {
            "tags_api_url": args.tags_api_url,
            "embeddings_api_url": args.embeddings_api_url,
            "tags_source": "aggregated_tags_service_via_app_api",
            "page_size": args.page_size,
            "batch_size": args.batch_size,
            "min_count": args.min_count,
            "max_tags": args.max_tags or None,
        },
        "projection": {
            "selected": args.projection,
            "fallbacks": {
                "api3d": "Use vectors3d_current from embeddings API.",
                "api3d_alt": "Use vectors3d_alt when the default 3D basis is visually weak.",
                "api2d_z": "Use vectors2d_current and synthesize z deterministically per tag.",
            },
        },
        "summary": {
            "tag_count_raw": len(tags),
            "point_count": len(points),
            "embedding_batch_count": len(embedding_batches),
            "embedding_modes": sorted({batch["response"].get("mode", "unknown") for batch in embedding_batches}),
        },
        "artifacts": output_paths,
        "ply_schema": {
            "format": "ascii 1.0",
            "vertex_fields": ["x", "y", "z", "count", "label_index"],
            "labels_by_id": [row["label"] for row in csv_rows],
        },
    }


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    page_size = max(1, min(500, int(args.page_size)))
    batch_size = max(1, min(80, int(args.batch_size)))
    max_links = max(8, min(400, int(args.max_links)))

    try:
        tags = fetch_all_tags(
            args.tags_api_url,
            page_size=page_size,
            max_tags=max(0, int(args.max_tags)),
            min_count=max(0, int(args.min_count)),
        )
        points, embedding_batches = fetch_embeddings(
            tags,
            embeddings_api_url=args.embeddings_api_url,
            batch_size=batch_size,
            projection=args.projection,
            min_sim=float(args.min_sim),
            max_links=max_links,
        )
    except urllib.error.URLError as exc:
        raise SystemExit(f"Network error while exporting tags: {exc}") from exc
    except (ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Invalid response while exporting tags: {exc}") from exc

    csv_rows = build_csv_rows(points)
    raw_tags_path = output_dir / "tags_raw.json"
    embeddings_path = output_dir / "tags_embeddings.json"
    csv_path = output_dir / "tags_points.csv"
    ply_path = output_dir / "tags_points.ply"
    metadata_path = output_dir / "metadata.json"

    output_paths = {
        "tags_raw_json": str(raw_tags_path),
        "tags_embeddings_json": str(embeddings_path),
        "tags_points_csv": str(csv_path),
        "tags_points_ply": str(ply_path),
        "metadata_json": str(metadata_path),
    }
    metadata = build_metadata(args, tags, points, csv_rows, embedding_batches, output_paths)

    write_json(raw_tags_path, {"tags": tags})
    write_json(
        embeddings_path,
        {
            "projection": args.projection,
            "points": points,
            "batches": embedding_batches,
        },
    )
    write_csv(csv_path, csv_rows)
    write_ply(ply_path, csv_rows)
    write_json(metadata_path, metadata)

    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
