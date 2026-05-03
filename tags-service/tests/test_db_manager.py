import unittest
from datetime import date

from app.api import db_manager


class _FakeResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self):
        return None


class _FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        self._csv_text = kwargs.pop("_csv_text", "")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url):
        return _FakeResponse(self._csv_text)


class DbManagerHelpersTest(unittest.TestCase):
    def test_parse_step_timestamp_to_utc_date(self):
        out = db_manager._parse_step_timestamp_to_utc_date("1774109239.143542")
        self.assertIsInstance(out, date)
        self.assertEqual(str(out), "2026-03-21")

    def test_parse_step_tags_json(self):
        tags = db_manager._parse_step_tags('["one","two",""]')
        self.assertEqual(tags, ["one", "two"])

    def test_parse_step_tags_python_literal(self):
        tags = db_manager._parse_step_tags("['alpha', 'beta']")
        self.assertEqual(tags, ["alpha", "beta"])

    def test_parse_step_tags_invalid(self):
        tags = db_manager._parse_step_tags("not-a-list")
        self.assertEqual(tags, [])


class BackfillFlowTest(unittest.IsolatedAsyncioTestCase):
    async def test_backfill_dry_run_counts_without_writes(self):
        csv_text = (
            "id,timestamp,tags\n"
            "1,1774109239.143542,\"['one','two']\"\n"
            "2,1774195639.143542,\"['two']\"\n"
        )
        original_client = db_manager.httpx.AsyncClient
        original_increment = db_manager.increment_daily_tag_count
        calls = []

        class _ClientFactory(_FakeAsyncClient):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs, _csv_text=csv_text)

        async def _increment(*args, **kwargs):
            calls.append((args, kwargs))

        try:
            db_manager.httpx.AsyncClient = _ClientFactory
            db_manager.increment_daily_tag_count = _increment
            result = await db_manager.backfill_daily_from_storage(
                storage_url="http://storage_service:8001",
                dry_run=True,
            )
        finally:
            db_manager.httpx.AsyncClient = original_client
            db_manager.increment_daily_tag_count = original_increment

        self.assertTrue(result["ok"])
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["processed_steps"], 2)
        self.assertEqual(result["used_steps"], 2)
        self.assertEqual(result["tag_increments"], 3)
        self.assertEqual(calls, [])

    async def test_backfill_writes_increment_calls(self):
        csv_text = (
            "id,timestamp,tags\n"
            "1,1774109239.143542,\"['one','two']\"\n"
        )
        original_client = db_manager.httpx.AsyncClient
        original_increment = db_manager.increment_daily_tag_count
        calls = []

        class _ClientFactory(_FakeAsyncClient):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs, _csv_text=csv_text)

        async def _increment(*args, **kwargs):
            calls.append((args, kwargs))

        try:
            db_manager.httpx.AsyncClient = _ClientFactory
            db_manager.increment_daily_tag_count = _increment
            result = await db_manager.backfill_daily_from_storage(
                storage_url="http://storage_service:8001",
                dry_run=False,
            )
        finally:
            db_manager.httpx.AsyncClient = original_client
            db_manager.increment_daily_tag_count = original_increment

        self.assertTrue(result["ok"])
        self.assertFalse(result["dry_run"])
        self.assertEqual(result["tag_increments"], 2)
        self.assertEqual(len(calls), 2)

