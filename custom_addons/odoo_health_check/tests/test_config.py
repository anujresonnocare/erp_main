from odoo.tests import tagged

from .common import OdooHealthTestCommon


@tagged("post_install", "-at_install", "odoo_health_check")
class TestConfigSettings(OdooHealthTestCommon):

    def test_notify_emails_roundtrip_via_settings(self):
        settings = self.env["res.config.settings"].create({
            "odoo_health_notify_emails": "a@x.com,b@y.com",
        })
        settings.execute()

        stored = self.Params.get_param("odoo_health_check.notify_emails")
        self.assertEqual(stored, "a@x.com,b@y.com")

    def test_retention_days_roundtrip_via_settings(self):
        settings = self.env["res.config.settings"].create({
            "odoo_health_retention_days": 45,
        })
        settings.execute()

        stored = self.Params.get_param("odoo_health_check.retention_days")
        self.assertEqual(stored, "45")

    def test_retention_cleanup_cron_registered_and_active(self):
        cron = self.env.ref(
            "odoo_health_check.ir_cron_history_retention_cleanup",
            raise_if_not_found=False,
        )
        self.assertTrue(cron, "retention cleanup cron must be registered on install")
        self.assertTrue(cron.active)
        self.assertEqual(cron.interval_type, "days")
        self.assertEqual(cron.interval_number, 1)
        self.assertIn("_cron_cleanup_history", cron.code)

    def test_failure_mail_template_registered(self):
        template = self.env.ref(
            "odoo_health_check.mail_template_cron_failure",
            raise_if_not_found=False,
        )
        self.assertTrue(template)
        self.assertEqual(template.model, "ir.cron.history")
        self.assertIn("Cron failure", template.subject)
