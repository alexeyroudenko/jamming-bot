#!/usr/bin/env python3
"""Перенос ожидающих в очереди ``do_screenshot`` из RQ ``default`` в ``screenshots``.

Запуск (образ app-service, каталог /app):
  python migrate_screenshot_jobs.py [--dry-run]

Имеет смысл один раз после вывода скринов в отдельную очередь и деплоя worker-screenshots.
"""
from __future__ import annotations

import argparse

from rq.job import Job

from rq_helpers import queue, redis_connection, screenshot_queue


def _is_screenshot_job(job: Job) -> bool:
    fn = getattr(job, "func_name", None) or ""
    return fn == "jobs.do_screenshot" or fn.endswith(".do_screenshot")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Только показать кандидатов")
    args = parser.parse_args()

    job_ids = list(queue.job_ids)
    moved = 0
    for jid in job_ids:
        try:
            job = Job.fetch(jid, connection=redis_connection)
        except Exception as exc:
            print(f"skip fetch {jid}: {exc}")
            continue
        if not _is_screenshot_job(job):
            continue
        label = "Would move" if args.dry_run else "Moving"
        print(f"{label} {jid} ({job.func_name})")
        if args.dry_run:
            moved += 1
            continue
        queue.remove(jid)
        screenshot_queue.enqueue_job(job)
        moved += 1

    prefix = "Would move" if args.dry_run else "Moved"
    print(f"Done. {prefix} {moved} job(s).")


if __name__ == "__main__":
    main()
