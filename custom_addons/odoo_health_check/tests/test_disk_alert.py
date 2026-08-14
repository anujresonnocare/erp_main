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
class TestDiskThresholds(OdooHealthTestCommon):
    """Cover _disk_thresholds() reading from ir.config_parameter."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Result = cls.env["health.check.result"]

    def _set(self, key, value):
        self.Params.set_param(f"odoo_health_check.{key}", str(value))

    def test_defaults_when_not_configured(self):
        self._set("disk_warn_pct", "")
        self._set("disk_critical_pct", "")
        self.assertEqual(self.Result._disk_thresholds(), (80.0, 90.0))

    def test_reads_from_settings(self):
        self._set("disk_warn_pct", "70")
        self._set("disk_critical_pct", "85")
        self.assertEqual(self.Result._disk_thresholds(), (70.0, 85.0))

    def test_invalid_values_fall_back_to_defaults(self):
        self._set("disk_warn_pct", "not-a-number")
        self._set("disk_critical_pct", "85")
        self.assertEqual(self.Result._disk_thresholds(), (80.0, 85.0))

    def test_clamps_out_of_range_values(self):
        self._set("disk_warn_pct", "-10")
        self._set("disk_critical_pct", "150")
        self.assertEqual(self.Result._disk_thresholds(), (0.0, 100.0))

    def test_critical_below_warn_falls_back_to_defaults(self):
        self._set("disk_warn_pct", "90")
        self._set("disk_critical_pct", "70")
        with mute_logger("odoo.addons.odoo_health_check.models.health_check_result"):
            self.assertEqual(self.Result._disk_thresholds(), (80.0, 90.0))

    def test_classification_uses_configured_thresholds(self):
        self._set("disk_warn_pct", "60")
        self._set("disk_critical_pct", "80")
        self.assertEqual(self.Result._classify_disk(50.0), "ok")
        self.assertEqual(self.Result._classify_disk(60.0), "warn")
        self.assertEqual(self.Result._classify_disk(80.0), "critical")


@tagged("post_install", "-at_install", "odoo_health_check")
class TestDiskAlertEmail(OdooHealthTestCommon):
    """Cover _send_disk_alert: transitions, recipient gating, isolation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Result = cls.env["health.check.result"]
        cls.Mail = cls.env["mail.mail"]

    def _set_recipients(self, value):
        self.Params.set_param("odoo_health_check.disk_alert_emails", value)

    def _seed(self, check_type, status):
        """Create a prior result row with given status without going through
        shutil. Bypasses the alert hook entirely (uses bare create)."""
        return self.Result.create({
            "check_type": check_type,
            "status": status,
            "mount_path": "/",
            "total_bytes": 1000.0,
            "free_bytes": 500.0,
            "used_pct": 50.0,
        })

    def test_first_run_warn_enqueues_alert(self):
        self._set_recipients("ops@example.com")
        before = self.Mail.search_count([])
        with patch(MOCK_PATH, return_value=_usage(1000, 850)):
            row = self.Result._sample_disk("disk_root", "/")
        self.assertEqual(row.status, "warn")
        self.assertEqual(self.Mail.search_count([]) - before, 1)
        mail = self.Mail.search([], order="id desc", limit=1)
        self.assertEqual(mail.email_to, "ops@example.com")
        self.assertIn("warn", mail.subject)

    def test_first_run_critical_enqueues_alert(self):
        self._set_recipients("ops@example.com")
        before = self.Mail.search_count([])
        with patch(MOCK_PATH, return_value=_usage(1000, 950)):
            self.Result._sample_disk("disk_root", "/")
        self.assertEqual(self.Mail.search_count([]) - before, 1)

    def test_warn_to_critical_enqueues_alert(self):
        self._set_recipients("ops@example.com")
        self._seed("disk_root", "warn")
        before = self.Mail.search_count([])
        with patch(MOCK_PATH, return_value=_usage(1000, 950)):
            self.Result._sample_disk("disk_root", "/")
        self.assertEqual(self.Mail.search_count([]) - before, 1)

    def test_warn_to_warn_does_not_enqueue(self):
        self._set_recipients("ops@example.com")
        self._seed("disk_root", "warn")
        before = self.Mail.search_count([])
        with patch(MOCK_PATH, return_value=_usage(1000, 850)):
            self.Result._sample_disk("disk_root", "/")
        self.assertEqual(self.Mail.search_count([]), before)

    def test_critical_to_critical_does_not_enqueue(self):
        self._set_recipients("ops@example.com")
        self._seed("disk_root", "critical")
        before = self.Mail.search_count([])
        with patch(MOCK_PATH, return_value=_usage(1000, 950)):
            self.Result._sample_disk("disk_root", "/")
        self.assertEqual(self.Mail.search_count([]), before)

    def test_critical_to_warn_does_not_enqueue(self):
        # Improvement, not worsening - no alert.
        self._set_recipients("ops@example.com")
        self._seed("disk_root", "critical")
        before = self.Mail.search_count([])
        with patch(MOCK_PATH, return_value=_usage(1000, 850)):
            self.Result._sample_disk("disk_root", "/")
        self.assertEqual(self.Mail.search_count([]), before)

    def test_ok_status_never_enqueues(self):
        self._set_recipients("ops@example.com")
        before = self.Mail.search_count([])
        with patch(MOCK_PATH, return_value=_usage(1000, 100)):
            self.Result._sample_disk("disk_root", "/")
        self.assertEqual(self.Mail.search_count([]), before)

    def test_error_status_never_enqueues(self):
        self._set_recipients("ops@example.com")
        before = self.Mail.search_count([])
        with patch(MOCK_PATH, side_effect=OSError("boom")), \
             mute_logger("odoo.addons.odoo_health_check.models.health_check_result"):
            self.Result._sample_disk("disk_root", "/")
        self.assertEqual(self.Mail.search_count([]), before)

    def test_empty_recipients_disable_alert(self):
        self._set_recipients("")
        before = self.Mail.search_count([])
        with patch(MOCK_PATH, return_value=_usage(1000, 950)):
            self.Result._sample_disk("disk_root", "/")
        self.assertEqual(self.Mail.search_count([]), before)

    def test_intermediate_error_row_is_skipped_when_finding_previous(self):
        # ok -> error -> warn should still send alert because the last
        # non-error sample was ok.
        self._set_recipients("ops@example.com")
        self._seed("disk_root", "ok")
        self.Result.create({
            "check_type": "disk_root",
            "status": "error",
            "mount_path": "/",
        })
        before = self.Mail.search_count([])
        with patch(MOCK_PATH, return_value=_usage(1000, 850)):
            self.Result._sample_disk("disk_root", "/")
        self.assertEqual(self.Mail.search_count([]) - before, 1)

    def test_alert_isolated_per_check_type(self):
        # disk_root warn doesn't suppress disk_filestore warn alert.
        self._set_recipients("ops@example.com")
        self._seed("disk_root", "warn")
        before = self.Mail.search_count([])
        with patch(MOCK_PATH, return_value=_usage(1000, 850)):
            self.Result._sample_disk("disk_filestore", "/var/lib/odoo")
        self.assertEqual(self.Mail.search_count([]) - before, 1)

    def test_multiple_recipients_comma_trimmed(self):
        self._set_recipients("  a@x.com , b@y.com  ")
        with patch(MOCK_PATH, return_value=_usage(1000, 850)):
            self.Result._sample_disk("disk_root", "/")
        mail = self.Mail.search([], order="id desc", limit=1)
        self.assertEqual(mail.email_to, "a@x.com,b@y.com")


@tagged("post_install", "-at_install", "odoo_health_check")
class TestDiskAlertConfig(OdooHealthTestCommon):
    """Cover settings roundtrip and template registration."""

    def test_warn_pct_roundtrip(self):
        settings = self.env["res.config.settings"].create({
            "odoo_health_disk_warn_pct": 75.5,
        })
        settings.execute()
        stored = self.Params.get_param("odoo_health_check.disk_warn_pct")
        self.assertEqual(float(stored), 75.5)

    def test_critical_pct_roundtrip(self):
        settings = self.env["res.config.settings"].create({
            "odoo_health_disk_critical_pct": 92.0,
        })
        settings.execute()
        stored = self.Params.get_param("odoo_health_check.disk_critical_pct")
        self.assertEqual(float(stored), 92.0)

    def test_alert_emails_roundtrip(self):
        settings = self.env["res.config.settings"].create({
            "odoo_health_disk_alert_emails": "a@x.com,b@y.com",
        })
        settings.execute()
        stored = self.Params.get_param("odoo_health_check.disk_alert_emails")
        self.assertEqual(stored, "a@x.com,b@y.com")

    def test_disk_alert_template_registered(self):
        template = self.env.ref(
            "odoo_health_check.mail_template_disk_alert",
            raise_if_not_found=False,
        )
        self.assertTrue(template)
        self.assertEqual(template.model, "health.check.result")
        self.assertIn("Disk", template.subject)
