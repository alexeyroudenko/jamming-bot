#!/usr/bin/env python3
import argparse
import json
import math
import os
import struct
import urllib.error
import urllib.request
import zlib
from pathlib import Path


DEFAULT_API_URL = "https://jamming-bot.arthew0.online/api/storage_ids/"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "out" / "render_ids"
DEFAULT_DOWNSAMPLED_MAX_SIDE = 2048


def parse_args():
    parser = argparse.ArgumentParser(
        description="Render storage step presence into PNG files."
    )
    parser.add_argument(
        "--api-url",
        default=os.getenv("RENDER_IDS_API_URL", DEFAULT_API_URL),
        help="Endpoint returning step ids, default: %(default)s",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for PNG artifacts, default: %(default)s",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=0,
        help="Canvas width. If omitted, chosen automatically from max step id.",
    )
    parser.add_argument(
        "--downsampled-max-side",
        type=int,
        default=DEFAULT_DOWNSAMPLED_MAX_SIDE,
        help="Max side length for downsampled PNG, default: %(default)s",
    )
    return parser.parse_args()


def fetch_json(url):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "render-ids-mvp/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def extract_step_ids(payload):
    if isinstance(payload, dict):
        if isinstance(payload.get("data"), list):
            raw_ids = payload["data"]
        elif isinstance(payload.get("ids"), list):
            raw_ids = payload["ids"]
        else:
            raise ValueError("Unsupported JSON payload: expected list in data or ids")
    elif isinstance(payload, list):
        raw_ids = payload
    else:
        raise ValueError("Unsupported JSON payload type")

    step_ids = sorted(
        {
            int(float(value))
            for value in raw_ids
            if value is not None and str(value).strip() != ""
        }
    )
    if not step_ids:
        raise ValueError("No step ids returned by API")
    return step_ids


def choose_dimensions(max_step_id, requested_width):
    if requested_width and requested_width > 0:
        width = requested_width
    else:
        width = max(1, math.ceil(math.sqrt(max_step_id + 1)))
    height = max(1, math.ceil((max_step_id + 1) / width))
    return width, height


def rasterize_presence(step_ids, width, height):
    rows = [bytearray(width) for _ in range(height)]
    for step_id in step_ids:
        x = step_id % width
        y = step_id // width
        if y < height:
            rows[y][x] = 255
    return rows


def downsample_presence(step_ids, src_width, src_height, max_side):
    if max(src_width, src_height) <= max_side:
        width = src_width
        height = src_height
    elif src_width >= src_height:
        scale = max_side / src_width
        width = max_side
        height = max(1, math.ceil(src_height * scale))
    else:
        scale = max_side / src_height
        height = max_side
        width = max(1, math.ceil(src_width * scale))

    rows = [bytearray(width) for _ in range(height)]
    for step_id in step_ids:
        src_x = step_id % src_width
        src_y = step_id // src_width
        dst_x = min(width - 1, int(src_x * width / src_width))
        dst_y = min(height - 1, int(src_y * height / src_height))
        rows[dst_y][dst_x] = 255
    return rows, width, height


def png_chunk(tag, data):
    return (
        struct.pack("!I", len(data))
        + tag
        + data
        + struct.pack("!I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def write_grayscale_png(path, rows, width, height):
    raw = b"".join(b"\x00" + bytes(row) for row in rows)
    header = struct.pack("!2I5B", width, height, 8, 0, 0, 0, 0)
    png = [
        b"\x89PNG\r\n\x1a\n",
        png_chunk(b"IHDR", header),
        png_chunk(b"IDAT", zlib.compress(raw, level=9)),
        png_chunk(b"IEND", b""),
    ]
    path.write_bytes(b"".join(png))


def write_metadata(path, metadata):
    path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        payload = fetch_json(args.api_url)
        step_ids = extract_step_ids(payload)
    except urllib.error.URLError as exc:
        raise SystemExit(f"Failed to fetch {args.api_url}: {exc}") from exc
    except (ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Invalid API response from {args.api_url}: {exc}") from exc

    max_step_id = step_ids[-1]
    width, height = choose_dimensions(max_step_id, args.width)
    raw_rows = rasterize_presence(step_ids, width, height)
    downsampled_rows, downsampled_width, downsampled_height = downsample_presence(
        step_ids,
        width,
        height,
        max(1, args.downsampled_max_side),
    )

    raw_path = output_dir / "presence_raw.png"
    downsampled_path = output_dir / "presence_downsampled.png"
    metadata_path = output_dir / "presence_metadata.json"

    write_grayscale_png(raw_path, raw_rows, width, height)
    write_grayscale_png(
        downsampled_path,
        downsampled_rows,
        downsampled_width,
        downsampled_height,
    )

    metadata = {
        "api_url": args.api_url,
        "step_count": len(step_ids),
        "min_step_id": step_ids[0],
        "max_step_id": max_step_id,
        "raw": {
            "width": width,
            "height": height,
            "path": str(raw_path),
        },
        "downsampled": {
            "width": downsampled_width,
            "height": downsampled_height,
            "path": str(downsampled_path),
        },
    }
    write_metadata(metadata_path, metadata)

    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
