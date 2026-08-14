import json
from collections import namedtuple
from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import OdooHealthTestCommon

DiskUsage = namedtuple("DiskUsage", ["total", "used", "free"])

MOCK_PATH = "odoo.addons.odoo_health_check.models.health_check_result.shutil.disk_usage"


def _usage(total, used):
    return DiskUsage(total=total, used=used, free=total - used)


@tagged("post_install", "-at_install", "odoo_health_check")
class TestDiskCheck(OdooHealthTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Result = cls.env["health.check.result"]

    def test_classify_thresholds_boundaries(self):
        cases = [
            (0.0, "ok"),
            (79.99, "ok"),
            (80.0, "warn"),
            (89.99, "warn"),
            (90.0, "critical"),
            (100.0, "critical"),
        ]
        for pct, expected in cases:
            with self.subTest(pct=pct):
                self.assertEqual(self.Result._classify_disk(pct), expected)

    def test_sample_disk_ok(self):
        usage = _usage(total=1000, used=500)
        with patch(MOCK_PATH, return_value=usage):
            row = self.Result._sample_disk("disk_root", "/")
        self.assertEqual(row.check_type, "disk_root")
        self.assertEqual(row.status, "ok")
        self.assertEqual(row.mount_path, "/")
        self.assertEqual(row.total_bytes, 1000)
        self.assertEqual(row.free_bytes, 500)
        self.assertEqual(row.used_pct, 50.0)
        self.assertFalse(row.details_json)

    def test_sample_disk_warn(self):
        with patch(MOCK_PATH, return_value=_usage(1000, 850)):
            row = self.Result._sample_disk("disk_filestore", "/var/lib/odoo")
        self.assertEqual(row.status, "warn")
        self.assertEqual(row.used_pct, 85.0)

    def test_sample_disk_critical(self):
        with patch(MOCK_PATH, return_value=_usage(1000, 950)):
            row = self.Result._sample_disk("disk_root", "/")
        self.assertEqual(row.status, "critical")
        self.assertEqual(row.used_pct, 95.0)

    def test_sample_disk_handles_large_byte_counts(self):
        # Regression: fields.Integer overflowed at >2.1 GB (int4 ceiling).
        # Use a 4 TB volume to ensure numeric storage holds it.
        four_tb = 4 * 1024**4
        with patch(MOCK_PATH, return_value=_usage(four_tb, four_tb // 2)):
            row = self.Result._sample_disk("disk_root", "/")
        self.assertEqual(row.total_bytes, float(four_tb))
        self.assertEqual(row.free_bytes, float(four_tb // 2))
        self.assertEqual(row.used_pct, 50.0)
        self.assertEqual(row.status, "ok")

    def test_sample_disk_zero_total_does_not_divide_by_zero(self):
        with patch(MOCK_PATH, return_value=_usage(0, 0)):
            row = self.Result._sample_disk("disk_root", "/")
        self.assertEqual(row.status, "ok")
        self.assertEqual(row.used_pct, 0.0)

    def test_sample_disk_error_path_creates_error_row(self):
        with patch(MOCK_PATH, side_effect=OSError("permission denied")), \
             mute_logger("odoo.addons.odoo_health_check.models.health_check_result"):
            row = self.Result._sample_disk("disk_root", "/missing")
        self.assertEqual(row.status, "error")
        self.assertEqual(row.check_type, "disk_root")
        self.assertEqual(row.mount_path, "/missing")
        details = json.loads(row.details_json)
        self.assertEqual(details["type"], "OSError")
        self.assertIn("permission denied", details["error"])

    def test_cron_check_disk_creates_one_row_per_target(self):
        before_ids = self.Result.search([]).ids
        with patch(MOCK_PATH, return_value=_usage(1000, 100)):
            self.Result._cron_check_disk()
        rows = self.Result.search([("id", "not in", before_ids)])
        self.assertEqual(len(rows), 2)
        types = sorted(rows.mapped("check_type"))
        self.assertEqual(types, ["disk_filestore", "disk_root"])
        for row in rows:
            self.assertEqual(row.status, "ok")
            self.assertEqual(row.used_pct, 10.0)

    def test_cron_check_disk_isolates_failures_per_target(self):
        # First call (disk_root) succeeds, second (disk_filestore) raises.
        side = [_usage(1000, 200), OSError("filestore unreachable")]

        def fake(_path):
            v = side.pop(0)
            if isinstance(v, Exception):
                raise v
            return v

        before_ids = self.Result.search([]).ids
        with patch(MOCK_PATH, side_effect=fake), \
             mute_logger("odoo.addons.odoo_health_check.models.health_check_result"):
            self.Result._cron_check_disk()
        rows = self.Result.search([("id", "not in", before_ids)])

        by_type = {r.check_type: r for r in rows}
        self.assertEqual(by_type["disk_root"].status, "ok")
        self.assertEqual(by_type["disk_filestore"].status, "error")

    def test_disk_check_cron_registered(self):
        cron = self.env.ref(
            "odoo_health_check.ir_cron_health_disk_check",
            raise_if_not_found=False,
        )
        self.assertTrue(cron, "disk check cron must be registered on install")
        self.assertTrue(cron.active)
        self.assertEqual(cron.interval_type, "hours")
        self.assertEqual(cron.interval_number, 1)
        self.assertIn("_cron_check_disk", cron.code)

    def test_action_url_for_disk_uses_disk_action(self):
        with patch(MOCK_PATH, return_value=_usage(1000, 500)):
            row = self.Result._sample_disk("disk_root", "/")
        action = self.env.ref("odoo_health_check.health_check_result_action")
        url = row._action_url()
        self.assertIn(f"/odoo/action-{action.id}/", url)
        self.assertTrue(url.endswith(f"/{row.id}"))

    def test_action_url_for_pg_report_uses_pg_action(self):
        row = self.Result.create({
            "check_type": "pg_report",
            "status": "ok",
            "details_json": "{}",
        })
        pg_action = self.env.ref("odoo_health_check.health_check_pg_report_action")
        disk_action = self.env.ref("odoo_health_check.health_check_result_action")
        url = row._action_url()
        self.assertIn(f"/odoo/action-{pg_action.id}/", url)
        self.assertNotIn(f"/odoo/action-{disk_action.id}/", url)
