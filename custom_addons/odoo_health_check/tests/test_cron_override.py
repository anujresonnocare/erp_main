from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import OdooHealthTestCommon


@tagged("post_install", "-at_install", "odoo_health_check")
class TestCronOverride(OdooHealthTestCommon):

    def test_callback_records_success(self):
        cron = self._make_cron(code="pass")
        before = self.History.search_count([("cron_id", "=", cron.id)])

        cron._callback(cron.name, cron.ir_actions_server_id.id)

        records = self.History.search(
            [("cron_id", "=", cron.id)], order="id desc",
        )
        self.assertEqual(len(records) - before, 1)
        self.assertEqual(records[0].state, "success")
        self.assertTrue(records[0].date_end)
        self.assertGreaterEqual(records[0].duration_sec, 0.0)
        self.assertFalse(records[0].error_traceback)

    def test_callback_records_failure_with_traceback(self):
        cron = self._make_cron(code="raise Exception('test boom')")

        with self.assertRaises(Exception) as ctx, mute_logger("odoo.addons.base.models.ir_cron"):
            cron._callback(cron.name, cron.ir_actions_server_id.id)
        self.assertIn("test boom", str(ctx.exception))

        record = self.History.search(
            [("cron_id", "=", cron.id)], order="id desc", limit=1,
        )
        self.assertEqual(record.state, "failed")
        self.assertIn("test boom", record.error_traceback or "")
        self.assertTrue(record.date_end)

    def test_manual_trigger_records_success(self):
        cron = self._make_cron(code="pass")

        cron.method_direct_trigger()

        record = self.History.search(
            [("cron_id", "=", cron.id)], order="id desc", limit=1,
        )
        self.assertEqual(record.state, "success")

    def test_manual_trigger_records_failure(self):
        cron = self._make_cron(code="raise Exception('manual boom')")

        with self.assertRaises(Exception) as ctx, mute_logger("odoo.addons.base.models.ir_actions"):
            cron.method_direct_trigger()
        self.assertIn("manual boom", str(ctx.exception))

        record = self.History.search(
            [("cron_id", "=", cron.id)], order="id desc", limit=1,
        )
        self.assertEqual(record.state, "failed")
        self.assertIn("manual boom", record.error_traceback or "")

    def test_cron_survives_missing_history_id(self):
        """If _odoo_health_log_start returns None (its own exception path),
        _callback must still run the super() implementation without raising
        from the logging side."""
        cron = self._make_cron(code="pass")
        with patch.object(type(cron), "_odoo_health_log_start", return_value=None):
            cron._callback(cron.name, cron.ir_actions_server_id.id)
