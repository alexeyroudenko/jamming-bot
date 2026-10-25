import os
from fastapi import APIRouter, HTTPException
from app.api.models import GeoOut
import maxminddb

ip = APIRouter()

MMDB_PATH = os.getenv("IP_MMDB_PATH", "data/db/dbip-city-lite.mmdb")


def _name_en(node) -> str:
    """Extract English (or first) name from MaxMind/DB-IP nested or flat city/country nodes."""
    if not node:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, dict):
        names = node.get("names")
        if isinstance(names, dict):
            return names.get("en") or next(iter(names.values()), "") or ""
        return node.get("name") or ""
    return ""


def _parse_record(record: dict) -> tuple[str, float, float]:
    """Support MaxMind GeoLite2 and DB-IP City Lite MMDB shapes."""
    city = _name_en(record.get("city"))

    lat, lon = 0.0, 0.0
    loc = record.get("location")
    if isinstance(loc, dict):
        lat = float(loc.get("latitude") or 0)
        lon = float(loc.get("longitude") or 0)
    else:
        # Flat DB-IP fields
        if record.get("latitude") is not None:
            lat = float(record["latitude"])
        if record.get("longitude") is not None:
            lon = float(record["longitude"])

    return city, lat, lon


@ip.get("/{ip}/")
async def get_geo(ip: str):
    out = GeoOut()
    if not ip:
        raise HTTPException(status_code=404, detail="ip not found")

    out.ip = ip
    out.city = ""
    out.latitude = 0
    out.longitude = 0
    out.error = ""

    if not os.path.isfile(MMDB_PATH):
        out.error = f"GeoIP DB not found: {MMDB_PATH} (set IP_MMDB_PATH and mount the .mmdb file)"
        return out

    try:
        with maxminddb.open_database(MMDB_PATH) as reader:
            record = reader.get(ip)
            if not record:
                out.error = "not found"
                return out
            city, lat, lon = _parse_record(record)
            out.city = city
            out.latitude = lat
            out.longitude = lon
    except Exception as e:
        out.error = str(e)

    return out
