import json
from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from .common import OdooHealthTestCommon


@tagged("post_install", "-at_install", "odoo_health_check")
class TestDashboard(OdooHealthTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Dashboard = cls.env["health.check.dashboard"]
        cls.Result = cls.env["health.check.result"]

    def _seed_disk(self, check_type, status, used_pct=50.0, total=1_000_000_000_000,
                   used=500_000_000_000, mount="/"):
        return self.Result.create({
            "check_type": check_type,
            "status": status,
            "used_pct": used_pct,
            "total_bytes": total,
            "free_bytes": total - used,
            "mount_path": mount,
        })

    def _seed_pg_report(self, payload, status="ok"):
        return self.Result.create({
            "check_type": "pg_report",
            "status": status,
            "details_json": json.dumps(payload),
        })

    def test_empty_state_unknown_disk_no_pg_report(self):
        snap = self.Dashboard._compute_dashboard_snapshot()
        self.assertEqual(snap["disk_root_status"], "unknown")
        self.assertEqual(snap["disk_filestore_status"], "unknown")
        self.assertFalse(snap["disk_root_at"])
        self.assertFalse(snap["last_pg_report_at"])
        self.assertIn("Not generated yet", snap["last_pg_report_db_delta"])

    def test_disk_tile_reads_latest_row_per_check_type(self):
        # Seed multiple rows; dashboard must pick the latest by date.
        old = self._seed_disk("disk_root", "warn", used_pct=85.0)
        old.date = fields.Datetime.now() - timedelta(hours=2)
        self._seed_disk("disk_root", "ok", used_pct=40.0)
        snap = self.Dashboard._compute_dashboard_snapshot()
        self.assertEqual(snap["disk_root_status"], "ok")
        self.assertEqual(snap["disk_root_used_pct"], 40.0)

    def test_disk_tile_isolation_per_check_type(self):
        self._seed_disk("disk_root", "critical", used_pct=95.0)
        self._seed_disk("disk_filestore", "ok", used_pct=10.0,
                        total=10_000_000_000, used=1_000_000_000,
                        mount="/var/lib/odoo")
        snap = self.Dashboard._compute_dashboard_snapshot()
        self.assertEqual(snap["disk_root_status"], "critical")
        self.assertEqual(snap["disk_filestore_status"], "ok")

    def test_disk_tile_error_status(self):
        self._seed_disk("disk_root", "error", mount="/missing")
        snap = self.Dashboard._compute_dashboard_snapshot()
        self.assertEqual(snap["disk_root_status"], "error")
        self.assertIn("/missing", snap["disk_root_summary"])

    def test_disk_summary_human_readable(self):
        self._seed_disk("disk_root", "ok",
                        total=1_073_741_824,  # 1 GiB
                        used=536_870_912,     # 512 MiB
                        used_pct=50.0,
                        mount="/")
        snap = self.Dashboard._compute_dashboard_snapshot()
        self.assertIn("1.0 GB", snap["disk_root_summary"])
        self.assertIn("512.0 MB", snap["disk_root_summary"])

    def test_failures_window_counts_only_failed_in_range(self):
        cron = self._make_cron()
        now = fields.Datetime.now()
        self.History.create({
            "cron_id": cron.id, "state": "failed",
            "date_start": now - timedelta(hours=2),
        })
        self.History.create({
            "cron_id": cron.id, "state": "failed",
            "date_start": now - timedelta(days=3),
        })
        self.History.create({
            "cron_id": cron.id, "state": "success",
            "date_start": now - timedelta(hours=1),
        })
        self.History.create({
            "cron_id": cron.id, "state": "failed",
            "date_start": now - timedelta(days=10),  # outside both windows
        })
        snap = self.Dashboard._compute_dashboard_snapshot()
        self.assertEqual(snap["failures_24h"], 1)
        self.assertEqual(snap["failures_7d"], 2)
        self.assertEqual(snap["history_total_7d"], 3)

    def test_pg_report_tile_reads_latest_ok_row(self):
        # An older first report
        old = self._seed_pg_report({
            "db_name": "test_db",
            "total_db_bytes": 50_000_000,
            "total_db_bytes_delta": None,
            "tables": [{"name": "ir_attachment", "total_bytes": 10_000_000,
                        "row_estimate": 100, "total_bytes_delta": None,
                        "row_estimate_delta": None}],
        })
        old.date = fields.Datetime.now() - timedelta(days=30)
        # Newer report
        self._seed_pg_report({
            "db_name": "test_db",
            "total_db_bytes": 60_000_000,
            "total_db_bytes_delta": 10_000_000,
            "tables": [{"name": "ir_attachment", "total_bytes": 12_000_000,
                        "row_estimate": 120, "total_bytes_delta": 2_000_000,
                        "row_estimate_delta": 20}],
        })
        snap = self.Dashboard._compute_dashboard_snapshot()
        self.assertTrue(snap["last_pg_report_at"])
        self.assertIn("MB", snap["last_pg_report_db_size"])
        self.assertIn("+", snap["last_pg_report_db_delta"])
        self.assertIn("ir_attachment", snap["last_pg_report_table"])

    def test_pg_report_tile_skips_error_rows(self):
        self._seed_pg_report({}, status="error")
        snap = self.Dashboard._compute_dashboard_snapshot()
        self.assertFalse(snap["last_pg_report_at"])
        self.assertIn("Not generated yet", snap["last_pg_report_db_delta"])

    def test_pg_report_first_report_message(self):
        self._seed_pg_report({
            "db_name": "test_db",
            "total_db_bytes": 100_000,
            "total_db_bytes_delta": None,
            "tables": [],
        })
        snap = self.Dashboard._compute_dashboard_snapshot()
        self.assertIn("First report", snap["last_pg_report_db_delta"])

    def test_singleton_record_exposes_fresh_computed_snapshot(self):
        self._seed_disk("disk_root", "warn", used_pct=85.0)
        rec = self.Dashboard._get_singleton()
        rec.invalidate_recordset()
        self.assertEqual(rec.disk_root_status, "warn")
        self.assertEqual(rec.disk_root_used_pct, 85.0)

    def test_action_refresh_reuses_singleton_no_record_churn(self):
        before_count = self.Dashboard.search_count([])
        action = self.Dashboard.action_refresh()
        self.Dashboard.action_refresh()
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "health.check.dashboard")
        self.assertEqual(self.Dashboard.search_count([]), before_count,
                         "refresh must not create new dashboard rows")

    def test_action_open_returns_singleton_id(self):
        action = self.Dashboard.action_open()
        singleton = self.Dashboard._get_singleton()
        self.assertEqual(action["res_id"], singleton.id)
