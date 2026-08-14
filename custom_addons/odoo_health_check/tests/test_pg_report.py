import json
from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import OdooHealthTestCommon

PATH_TOP = "odoo.addons.odoo_health_check.models.health_check_result.HealthCheckResult._pg_top_tables"
PATH_DB = "odoo.addons.odoo_health_check.models.health_check_result.HealthCheckResult._pg_db_size"


def _table(name, total_bytes, table_bytes, row_estimate):
    return {
        "name": name,
        "total_bytes": total_bytes,
        "table_bytes": table_bytes,
        "row_estimate": row_estimate,
    }


@tagged("post_install", "-at_install", "odoo_health_check")
class TestPgReportSql(OdooHealthTestCommon):
    """Real SQL against the test DB - verifies query syntax + shape."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Result = cls.env["health.check.result"]

    def test_pg_top_tables_returns_dicts(self):
        rows = self.Result._pg_top_tables(limit=5)
        self.assertLessEqual(len(rows), 5)
        # Any Odoo DB has at least a few tables
        self.assertGreater(len(rows), 0)
        for r in rows:
            self.assertIn("name", r)
            self.assertIn("total_bytes", r)
            self.assertIn("table_bytes", r)
            self.assertIn("row_estimate", r)
            self.assertIsInstance(r["total_bytes"], int)

    def test_pg_top_tables_excludes_system_schemas(self):
        rows = self.Result._pg_top_tables(limit=50)
        names = {r["name"] for r in rows}
        # pg_class lives in pg_catalog and must not appear
        self.assertNotIn("pg_class", names)
        self.assertNotIn("pg_attribute", names)

    def test_pg_db_size_positive_int(self):
        size = self.Result._pg_db_size()
        self.assertIsInstance(size, int)
        self.assertGreater(size, 0)


@tagged("post_install", "-at_install", "odoo_health_check")
class TestPgReportRun(OdooHealthTestCommon):
    """Cover _cron_pg_report with mocked SQL helpers."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Result = cls.env["health.check.result"]
        cls.Mail = cls.env["mail.mail"]

    def setUp(self):
        super().setUp()
        # Wipe pg_report rows so 'first run' assertions stay deterministic
        # against dev DBs where the monthly cron may have fired for real.
        # The unlink rides the test savepoint and rolls back at test end.
        self.Result.search([("check_type", "=", "pg_report")]).unlink()

    def _set_recipients(self, value):
        self.Params.set_param("odoo_health_check.pg_report_emails", value)

    def test_first_run_creates_ok_row_with_snapshot(self):
        self._set_recipients("")
        with patch(PATH_TOP, return_value=[
            _table("res_users", 1_000_000, 800_000, 50),
            _table("ir_attachment", 5_000_000, 4_000_000, 200),
        ]), patch(PATH_DB, return_value=10_000_000):
            row = self.Result._cron_pg_report()
        self.assertEqual(row.check_type, "pg_report")
        self.assertEqual(row.status, "ok")
        data = json.loads(row.details_json)
        self.assertEqual(data["total_db_bytes"], 10_000_000)
        self.assertIsNone(data["total_db_bytes_delta"])  # no previous report
        self.assertEqual(len(data["tables"]), 2)
        # First run: every table is "new" (delta is None)
        for t in data["tables"]:
            self.assertIsNone(t["total_bytes_delta"])
            self.assertIsNone(t["row_estimate_delta"])

    def test_second_run_computes_deltas(self):
        self._set_recipients("")
        # First report
        with patch(PATH_TOP, return_value=[
            _table("res_users", 1_000_000, 800_000, 50),
            _table("ir_attachment", 5_000_000, 4_000_000, 200),
        ]), patch(PATH_DB, return_value=10_000_000):
            self.Result._cron_pg_report()
        # Second report - growth
        with patch(PATH_TOP, return_value=[
            _table("res_users", 1_500_000, 1_200_000, 60),
            _table("ir_attachment", 6_000_000, 5_000_000, 250),
            _table("brand_new_table", 100_000, 80_000, 5),
        ]), patch(PATH_DB, return_value=12_000_000):
            row = self.Result._cron_pg_report()
        data = json.loads(row.details_json)
        self.assertEqual(data["total_db_bytes_delta"], 2_000_000)
        by_name = {t["name"]: t for t in data["tables"]}
        self.assertEqual(by_name["res_users"]["total_bytes_delta"], 500_000)
        self.assertEqual(by_name["res_users"]["row_estimate_delta"], 10)
        self.assertEqual(by_name["ir_attachment"]["total_bytes_delta"], 1_000_000)
        self.assertIsNone(by_name["brand_new_table"]["total_bytes_delta"])

    def test_run_emails_when_recipients_set(self):
        self._set_recipients("dba@example.com")
        before = self.Mail.search_count([])
        with patch(PATH_TOP, return_value=[_table("foo", 100, 80, 5)]), \
             patch(PATH_DB, return_value=200):
            self.Result._cron_pg_report()
        self.assertEqual(self.Mail.search_count([]) - before, 1)
        mail = self.Mail.search([], order="id desc", limit=1)
        self.assertEqual(mail.email_to, "dba@example.com")
        self.assertIn("PG monthly report", mail.subject)

    def test_run_skips_email_when_recipients_empty(self):
        self._set_recipients("")
        before = self.Mail.search_count([])
        with patch(PATH_TOP, return_value=[_table("foo", 100, 80, 5)]), \
             patch(PATH_DB, return_value=200):
            self.Result._cron_pg_report()
        self.assertEqual(self.Mail.search_count([]), before)

    def test_run_records_error_row_on_sql_failure(self):
        self._set_recipients("dba@example.com")
        before = self.Mail.search_count([])
        with patch(PATH_TOP, side_effect=RuntimeError("simulated SQL error")), \
             mute_logger("odoo.addons.odoo_health_check.models.health_check_result"):
            row = self.Result._cron_pg_report()
        self.assertEqual(row.status, "error")
        details = json.loads(row.details_json)
        self.assertEqual(details["type"], "RuntimeError")
        self.assertIn("simulated SQL error", details["error"])
        # No email on error
        self.assertEqual(self.Mail.search_count([]), before)

    def test_diff_tables_handles_disappeared_table(self):
        # If a table existed last month but not this month, it's just not
        # in the current list - no error.
        current = [_table("a", 100, 80, 5)]
        previous = [
            {"name": "a", "total_bytes": 50, "table_bytes": 40, "row_estimate": 3},
            {"name": "dropped", "total_bytes": 999, "table_bytes": 800, "row_estimate": 50},
        ]
        annotated = self.env["health.check.result"]._diff_tables(current, previous)
        self.assertEqual(annotated[0]["total_bytes_delta"], 50)
        self.assertEqual(annotated[0]["row_estimate_delta"], 2)


@tagged("post_install", "-at_install", "odoo_health_check")
class TestPgReportConfig(OdooHealthTestCommon):

    def test_pg_report_emails_roundtrip(self):
        settings = self.env["res.config.settings"].create({
            "odoo_health_pg_report_emails": "a@x.com,b@y.com",
        })
        settings.execute()
        stored = self.Params.get_param("odoo_health_check.pg_report_emails")
        self.assertEqual(stored, "a@x.com,b@y.com")

    def test_pg_monthly_template_registered(self):
        template = self.env.ref(
            "odoo_health_check.mail_template_pg_monthly",
            raise_if_not_found=False,
        )
        self.assertTrue(template)
        self.assertEqual(template.model, "health.check.result")
        self.assertIn("PG monthly report", template.subject)

    def test_pg_report_cron_registered_monthly(self):
        cron = self.env.ref(
            "odoo_health_check.ir_cron_health_pg_report",
            raise_if_not_found=False,
        )
        self.assertTrue(cron, "PG report cron must be registered on install")
        self.assertTrue(cron.active)
        self.assertEqual(cron.interval_type, "months")
        self.assertEqual(cron.interval_number, 1)
        self.assertIn("_cron_pg_report", cron.code)


@tagged("post_install", "-at_install", "odoo_health_check")
class TestHumanByteFormatters(OdooHealthTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Result = cls.env["health.check.result"]

    def test_human_bytes_units(self):
        cases = [
            (0, "0.0 B"),
            (512, "512.0 B"),
            (1024, "1.0 KB"),
            (1024 * 1024, "1.0 MB"),
            (1024 ** 3, "1.0 GB"),
            (5 * 1024 ** 3, "5.0 GB"),
        ]
        for n, expected in cases:
            with self.subTest(n=n):
                self.assertEqual(self.Result._human_bytes(n), expected)

    def test_human_bytes_handles_none(self):
        self.assertEqual(self.Result._human_bytes(None), "")

    def test_human_delta_bytes_signs(self):
        self.assertEqual(self.Result._human_delta_bytes(0), "0 B")
        self.assertEqual(self.Result._human_delta_bytes(1024), "+1.0 KB")
        self.assertEqual(self.Result._human_delta_bytes(-1024), "-1.0 KB")
        self.assertEqual(self.Result._human_delta_bytes(None), "")
