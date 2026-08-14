from datetime import timedelta

import psycopg2
from odoo import fields
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import OdooHealthTestCommon


@tagged("post_install", "-at_install", "odoo_health_check")
class TestCronHistoryModel(OdooHealthTestCommon):

    def test_create_sets_defaults(self):
        cron = self._make_cron()
        hist = self.History.create({"cron_id": cron.id})
        self.assertEqual(hist.state, "running")
        self.assertTrue(hist.date_start)
        self.assertTrue(hist.server_name)
        self.assertFalse(hist.date_end)
        self.assertEqual(hist.duration_sec, 0.0)

    def test_duration_sec_computed_from_dates(self):
        cron = self._make_cron()
        hist = self.History.create({
            "cron_id": cron.id,
            "date_start": "2026-04-29 10:00:00",
        })
        hist.write({
            "state": "success",
            "date_end": "2026-04-29 10:00:42",
        })
        self.assertEqual(hist.duration_sec, 42.0)

    def test_date_order_constraint_violated_on_write(self):
        cron = self._make_cron()
        hist = self.History.create({"cron_id": cron.id})
        with self.assertRaises(psycopg2.IntegrityError), \
             mute_logger("odoo.sql_db"), \
             self.env.cr.savepoint():
            hist.write({
                "date_start": "2026-06-15 10:00:00",
                "date_end": "2026-06-15 09:00:00",
            })

    def test_cascade_delete_when_cron_removed(self):
        cron = self._make_cron()
        hist_id = self.History.create({"cron_id": cron.id}).id
        cron.unlink()
        self.assertFalse(self.History.browse(hist_id).exists())

    def test_cleanup_removes_old_keeps_recent(self):
        cron = self._make_cron()
        now = fields.Datetime.now()
        old = self.History.create({
            "cron_id": cron.id,
            "date_start": now - timedelta(days=60),
            "state": "success",
        })
        fresh = self.History.create({
            "cron_id": cron.id,
            "date_start": now - timedelta(days=5),
            "state": "success",
        })
        self.Params.set_param("odoo_health_check.retention_days", "30")

        removed = self.History._cron_cleanup_history()

        self.assertGreaterEqual(removed, 1)
        self.assertFalse(old.exists())
        self.assertTrue(fresh.exists())

    def test_cleanup_disabled_when_retention_non_positive(self):
        cron = self._make_cron()
        now = fields.Datetime.now()
        old = self.History.create({
            "cron_id": cron.id,
            "date_start": now - timedelta(days=60),
            "state": "success",
        })
        self.Params.set_param("odoo_health_check.retention_days", "0")

        removed = self.History._cron_cleanup_history()

        self.assertEqual(removed, 0)
        self.assertTrue(old.exists())

    def test_cleanup_ignores_invalid_param(self):
        cron = self._make_cron()
        now = fields.Datetime.now()
        self.History.create({
            "cron_id": cron.id,
            "date_start": now - timedelta(days=60),
            "state": "success",
        })
        self.Params.set_param("odoo_health_check.retention_days", "not-a-number")

        removed = self.History._cron_cleanup_history()

        self.assertEqual(removed, 0)

    def test_action_url_points_at_record_via_action(self):
        cron = self._make_cron()
        hist = self.History.create({"cron_id": cron.id})
        url = hist._action_url()
        action = self.env.ref("odoo_health_check.ir_cron_history_action")
        self.assertIn(f"/odoo/action-{action.id}/", url)
        self.assertTrue(url.endswith(f"/{hist.id}"))
