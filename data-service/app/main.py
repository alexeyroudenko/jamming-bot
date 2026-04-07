import csv
import io
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import StreamingResponse

DB_PATH = Path("/app/data/database.db")

app = FastAPI(
    title="Data Service",
    version="0.1.0",
    docs_url=None,
    openapi_url="/openapi.json",
)


@app.get("/docs", include_in_schema=False)
def swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="openapi.json",
        title=f"{app.title} - Swagger UI",
    )


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@contextmanager
def get_db():
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="Database file not found")
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


@app.get("/api/urls/stats")
def get_stats():
    with get_db() as conn:
        cur = conn.cursor()
        total = cur.execute("SELECT COUNT(*) FROM Urls").fetchone()[0]
        visited = cur.execute("SELECT COUNT(*) FROM Urls WHERE visited=1").fetchone()[0]
        hostnames = cur.execute("SELECT COUNT(DISTINCT hostname) FROM Urls").fetchone()[0]
    return {
        "total": total,
        "visited": visited,
        "unvisited": total - visited,
        "hostnames": hostnames,
    }


@app.get("/api/urls")
def get_urls(
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=500),
    visited: Optional[int] = Query(None, ge=0, le=1),
    hostname: Optional[str] = Query(None),
):
    conditions = []
    params = []

    if visited is not None:
        conditions.append("visited = ?")
        params.append(visited)
    if hostname:
        conditions.append("hostname = ?")
        params.append(hostname)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    offset = (page - 1) * per_page

    with get_db() as conn:
        cur = conn.cursor()

        total = cur.execute(f"SELECT COUNT(*) FROM Urls {where}", params).fetchone()[0]

        rows = cur.execute(
            f"SELECT id, hostname, url, src_url, visited FROM Urls {where} ORDER BY id LIMIT ? OFFSET ?",
            params + [per_page, offset],
        ).fetchall()

    return {
        "data": [dict(r) for r in rows],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": max(1, (total + per_page - 1) // per_page),
        },
    }


@app.get("/data/{row_id:int}/")
@app.get("/{row_id:int}/", include_in_schema=False)
def get_url_row_full(row_id: int):
    """
    Вся строка из SQLite `Urls` по `id` (в контексте бота обычно совпадает с номером шага).

    Снаружи: `https://data.jamming-bot.../data/1/` (путь на сервисе `/data/1/`).

    На основном хосте `https://jamming-bot.../data/1/` после strip префикса `/data` запрос приходит как `/1/`.
    """
    with get_db() as conn:
        row = conn.execute("SELECT * FROM Urls WHERE id = ?", (row_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No row with id={row_id}")
    return dict(row)


@app.get("/api/urls/hostnames")
def get_hostnames():
    """Distinct hostnames with counts."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT hostname, COUNT(*) as cnt FROM Urls GROUP BY hostname ORDER BY cnt DESC"
        ).fetchall()
    return {"data": [{"hostname": r["hostname"], "count": r["cnt"]} for r in rows]}


def _iter_csv(visited: Optional[int]):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "hostname", "url", "src_url", "visited"])
    yield buf.getvalue()
    buf.seek(0)
    buf.truncate(0)

    conditions = []
    params = []
    if visited is not None:
        conditions.append("visited = ?")
        params.append(visited)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        cur = conn.execute(
            f"SELECT id, hostname, url, src_url, visited FROM Urls {where} ORDER BY id",
            params,
        )
        while True:
            batch = cur.fetchmany(500)
            if not batch:
                break
            for row in batch:
                writer.writerow(row)
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate(0)
    finally:
        conn.close()


@app.get("/api/urls/export")
def export_csv(visited: Optional[int] = Query(None, ge=0, le=1)):
    return StreamingResponse(
        _iter_csv(visited),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="urls_export.csv"'},
    )
