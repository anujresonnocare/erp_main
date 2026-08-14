from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import OdooHealthTestCommon


@tagged("post_install", "-at_install", "odoo_health_check")
class TestFailureEmail(OdooHealthTestCommon):

    def _set_notify(self, value):
        self.Params.set_param("odoo_health_check.notify_emails", value)

    def test_failed_cron_with_recipients_enqueues_mail(self):
        self._set_notify("ops-test@example.com")
        cron = self._make_cron(code="raise ValueError('email test boom')")
        Mail = self.env["mail.mail"]
        before = Mail.search_count([])

        with self.assertRaises(ValueError), mute_logger("odoo.addons.base.models.ir_cron"):
            cron._callback(cron.name, cron.ir_actions_server_id.id)

        self.assertEqual(Mail.search_count([]) - before, 1)
        mail = Mail.search([], order="id desc", limit=1)
        self.assertEqual(mail.email_to, "ops-test@example.com")
        self.assertIn(cron.name, mail.subject)

    def test_failed_cron_with_empty_recipients_does_not_enqueue(self):
        self._set_notify("")
        cron = self._make_cron(code="raise ValueError('silent failure')")
        Mail = self.env["mail.mail"]
        before = Mail.search_count([])

        with self.assertRaises(ValueError), mute_logger("odoo.addons.base.models.ir_cron"):
            cron._callback(cron.name, cron.ir_actions_server_id.id)

        self.assertEqual(Mail.search_count([]), before)

    def test_successful_cron_never_enqueues_mail(self):
        self._set_notify("ops-test@example.com")
        cron = self._make_cron(code="pass")
        Mail = self.env["mail.mail"]
        before = Mail.search_count([])

        cron._callback(cron.name, cron.ir_actions_server_id.id)

        self.assertEqual(Mail.search_count([]), before)

    def test_multiple_recipients_comma_separated(self):
        self._set_notify(" a@x.com , b@y.com ,  ")
        cron = self._make_cron(code="raise ValueError('multi recipient')")
        Mail = self.env["mail.mail"]

        with self.assertRaises(ValueError), mute_logger("odoo.addons.base.models.ir_cron"):
            cron._callback(cron.name, cron.ir_actions_server_id.id)

        mail = Mail.search([], order="id desc", limit=1)
        self.assertEqual(mail.email_to, "a@x.com,b@y.com")
