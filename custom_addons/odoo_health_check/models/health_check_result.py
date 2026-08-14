import json
import logging
import shutil

from odoo import api, fields, models
from odoo.tools import config

_logger = logging.getLogger(__name__)

DEFAULT_WARN_PCT = 80.0
DEFAULT_CRITICAL_PCT = 90.0

# severity ordering for transition detection
_SEVERITY = {"ok": 0, "warn": 1, "critical": 2}

# Top tables by total relation size (table + indexes + toast). Excludes
# system schemas. reltuples is PostgreSQL's row estimate from the last
# ANALYZE - much faster than COUNT(*) on large tables and accurate enough
# for a monthly trend report.
_PG_TOP_TABLES_SQL = """
    SELECT
        c.relname AS table_name,
        pg_total_relation_size(c.oid)::bigint AS total_bytes,
        pg_relation_size(c.oid)::bigint AS table_bytes,
        c.reltuples::bigint AS row_estimate
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relkind = 'r'
      AND n.nspname NOT IN ('pg_catalog', 'information_schema')
    ORDER BY pg_total_relation_size(c.oid) DESC
    LIMIT %s
"""


def _human_bytes(n):
    """Format a byte count like '1.2 GB'. Handles negative values."""
    if n is None:
        return ""
    sign = "-" if n < 0 else ""
    n = abs(n)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if n < 1024.0:
            return f"{sign}{n:.1f} {unit}"
        n /= 1024.0
    return f"{sign}{n:.1f} EB"


def _human_delta_bytes(n):
    """Format a byte delta with explicit sign: '+1.2 GB' or '-300 MB'."""
    if n is None:
        return ""
    if n == 0:
        return "0 B"
    return ("+" if n > 0 else "") + _human_bytes(n)


class HealthCheckResult(models.Model):
    _name = "health.check.result"
    _description = "Health Check Result"
    _order = "date desc, id desc"
    _rec_name = "check_type"

    check_type = fields.Selection(
        [
            ("disk_root", "Disk: OS Root"),
            ("disk_filestore", "Disk: Odoo Filestore"),
            ("pg_report", "PostgreSQL Monthly Report"),
        ],
        required=True,
        index=True,
    )
    date = fields.Datetime(
        required=True,
        default=fields.Datetime.now,
        index=True,
    )
    status = fields.Selection(
        [
            ("ok", "OK"),
            ("warn", "Warning"),
            ("critical", "Critical"),
            ("error", "Error"),
        ],
        required=True,
        default="ok",
        index=True,
    )
    mount_path = fields.Char(
        string="Mount / Path",
    )
    total_bytes = fields.Float(
        digits=(20, 0),
    )
    free_bytes = fields.Float(
        digits=(20, 0),
    )
    used_pct = fields.Float(
        string="Used %",
        digits=(5, 2),
    )
    details_json = fields.Text(
        string="Details (JSON)",
        help="Raw details, error traceback, or extra metadata as JSON.",
    )

    @api.model
    def _get_float_param(self, key, default):
        """Read a float ir.config_parameter, falling back to default on
        missing or non-numeric values. Defaults are baked into the source
        rather than relying on res_config_settings so a fresh install
        without saved settings still has sane thresholds.
        """
        raw = self.env["ir.config_parameter"].sudo().get_param(key, default)
        try:
            return float(raw)
        except (TypeError, ValueError):
            return default

    @api.model
    def _disk_thresholds(self):
        """Return (warn_pct, critical_pct) clamped to [0, 100]. If the
        warn/critical invariant is violated (critical < warn), reverts
        both to defaults and logs.
        """
        warn = self._get_float_param("odoo_health_check.disk_warn_pct", DEFAULT_WARN_PCT)
        critical = self._get_float_param(
            "odoo_health_check.disk_critical_pct", DEFAULT_CRITICAL_PCT
        )
        warn = max(0.0, min(100.0, warn))
        critical = max(0.0, min(100.0, critical))
        if critical < warn:
            _logger.warning(
                "odoo_health_check: disk thresholds invariant violated "
                "(warn=%s critical=%s), falling back to defaults",
                warn, critical,
            )
            return (DEFAULT_WARN_PCT, DEFAULT_CRITICAL_PCT)
        return (warn, critical)

    @api.model
    def _classify_disk(self, used_pct):
        warn, critical = self._disk_thresholds()
        if used_pct >= critical:
            return "critical"
        if used_pct >= warn:
            return "warn"
        return "ok"

    @api.model
    def _disk_targets(self):
        """Return [(check_type, path), ...] for the disk checks.

        Filestore path is taken from `odoo.tools.config['data_dir']`,
        which on Odoo.sh and standard installs points at the per-DB
        filestore parent directory. shutil.disk_usage resolves to the
        underlying mount, so multi-mount setups work without extra logic.
        """
        data_dir = config.get("data_dir") or "/"
        return [
            ("disk_root", "/"),
            ("disk_filestore", data_dir),
        ]

    @api.model
    def _cron_check_disk(self):
        """Sample disk usage on OS root and Odoo filestore mount.

        Creates one health.check.result row per check_type. Never raises -
        any sampling failure is captured as a row with status='error' so
        the cron itself stays green.
        """
        for check_type, path in self._disk_targets():
            self._sample_disk(check_type, path)

    @api.model
    def _sample_disk(self, check_type, path):
        try:
            usage = shutil.disk_usage(path)
            used_pct = (usage.used / usage.total * 100.0) if usage.total else 0.0
            vals = {
                "check_type": check_type,
                "status": self._classify_disk(used_pct),
                "mount_path": path,
                "total_bytes": float(usage.total),
                "free_bytes": float(usage.free),
                "used_pct": round(used_pct, 2),
            }
        except Exception as exc:  # noqa: BLE001 - infra check, must not fail the cron
            _logger.exception(
                "odoo_health_check: disk check failed for %s (%s)",
                check_type,
                path,
            )
            vals = {
                "check_type": check_type,
                "status": "error",
                "mount_path": path,
                "details_json": json.dumps(
                    {"error": str(exc), "type": type(exc).__name__}
                ),
            }
        record = self.create(vals)
        record._send_disk_alert()
        return record

    def _send_disk_alert(self):
        """Enqueue a disk alert email if status worsened since last sample.

        Sends only on transitions where severity strictly increased
        (ok -> warn, ok -> critical, warn -> critical). 'error' rows
        never trigger an alert and are skipped when looking up the
        previous state, so a transient measurement failure between two
        ok samples doesn't generate spurious alerts.

        Disabled when `odoo_health_check.disk_alert_emails` is empty.
        """
        self.ensure_one()
        if self.status not in ("warn", "critical"):
            return
        recipients = self._get_disk_alert_recipients()
        if not recipients:
            return
        prev = self.search(
            [
                ("check_type", "=", self.check_type),
                ("status", "!=", "error"),
                ("id", "!=", self.id),
            ],
            order="date desc, id desc",
            limit=1,
        )
        prev_status = prev.status if prev else "ok"
        if _SEVERITY[self.status] <= _SEVERITY[prev_status]:
            return
        template = self.env.ref(
            "odoo_health_check.mail_template_disk_alert",
            raise_if_not_found=False,
        )
        if not template:
            _logger.warning(
                "odoo_health_check: disk alert template missing, skipping alert"
            )
            return
        # Narrow try/except: only the actual mail enqueue needs guarding.
        # A flaky mail server must not abort the disk check row write.
        try:
            template.send_mail(
                self.id,
                force_send=False,
                email_values={"email_to": ",".join(recipients)},
            )
        except Exception:
            _logger.exception(
                "odoo_health_check: failed to enqueue disk alert for result_id=%s",
                self.id,
            )

    @api.model
    def _get_disk_alert_recipients(self):
        raw = self.env["ir.config_parameter"].sudo().get_param(
            "odoo_health_check.disk_alert_emails", default="",
        ) or ""
        return [e.strip() for e in raw.split(",") if e.strip()]

    # ------------------------------------------------------------------
    # PG monthly growth report (Phase 8)
    # ------------------------------------------------------------------

    @api.model
    def _pg_top_tables(self, limit=10):
        """Return [{name, total_bytes, table_bytes, row_estimate}, ...]
        for the top-N tables by total relation size, excluding system
        schemas. Uses pg_class.reltuples (estimate) for row count."""
        self.env.cr.execute(_PG_TOP_TABLES_SQL, (limit,))
        return [
            {
                "name": name,
                "total_bytes": int(total_bytes or 0),
                "table_bytes": int(table_bytes or 0),
                "row_estimate": int(row_estimate or 0),
            }
            for name, total_bytes, table_bytes, row_estimate in self.env.cr.fetchall()
        ]

    @api.model
    def _pg_db_size(self):
        """Total size of the current database in bytes."""
        self.env.cr.execute("SELECT pg_database_size(current_database())::bigint")
        return int(self.env.cr.fetchone()[0] or 0)

    @staticmethod
    def _diff_tables(current, previous):
        """Annotate each entry in `current` with bytes/rows delta vs the
        same-named row in `previous`. New tables (not in previous) get
        delta=None to render as 'new' in the email."""
        prev_by_name = {t["name"]: t for t in previous} if previous else {}
        for cur in current:
            prev = prev_by_name.get(cur["name"])
            if prev is None:
                cur["total_bytes_delta"] = None
                cur["row_estimate_delta"] = None
            else:
                cur["total_bytes_delta"] = cur["total_bytes"] - prev["total_bytes"]
                cur["row_estimate_delta"] = (
                    cur["row_estimate"] - prev["row_estimate"]
                )
        return current

    @api.model
    def _cron_pg_report(self):
        """Generate a monthly PostgreSQL growth report, store the snapshot,
        and email it to configured recipients. Returns the created record.

        Never raises - SQL or storage failures are captured as a row with
        status='error' so the cron itself stays green.
        """
        try:
            tables = self._pg_top_tables(limit=10)
            db_size = self._pg_db_size()
            previous = self.search(
                [("check_type", "=", "pg_report"), ("status", "=", "ok")],
                order="date desc, id desc",
                limit=1,
            )
            prev_tables = []
            prev_db_size = None
            if previous and previous.details_json:
                try:
                    prev_data = json.loads(previous.details_json)
                    prev_tables = prev_data.get("tables") or []
                    prev_db_size = prev_data.get("total_db_bytes")
                except (ValueError, TypeError):
                    prev_tables = []
            tables = self._diff_tables(tables, prev_tables)
            payload = {
                "db_name": self.env.cr.dbname,
                "total_db_bytes": db_size,
                "total_db_bytes_delta": (
                    db_size - prev_db_size if prev_db_size is not None else None
                ),
                "tables": tables,
                "previous_report_id": previous.id if previous else None,
            }
            record = self.create({
                "check_type": "pg_report",
                "status": "ok",
                "details_json": json.dumps(payload),
            })
        except Exception as exc:  # noqa: BLE001 - infra check, must not fail the cron
            _logger.exception("odoo_health_check: pg report SQL failed")
            record = self.create({
                "check_type": "pg_report",
                "status": "error",
                "details_json": json.dumps(
                    {"error": str(exc), "type": type(exc).__name__}
                ),
            })
            return record
        record._send_pg_report_email()
        return record

    def _send_pg_report_email(self):
        """Send the monthly report. Skipped when recipients list is empty
        (the report row is still created)."""
        self.ensure_one()
        if self.status != "ok":
            return
        recipients = self._get_pg_report_recipients()
        if not recipients:
            return
        template = self.env.ref(
            "odoo_health_check.mail_template_pg_monthly",
            raise_if_not_found=False,
        )
        if not template:
            _logger.warning(
                "odoo_health_check: pg report template missing, skipping email"
            )
            return
        # Narrow try/except: only the mail enqueue needs guarding.
        try:
            template.send_mail(
                self.id,
                force_send=False,
                email_values={"email_to": ",".join(recipients)},
            )
        except Exception:
            _logger.exception(
                "odoo_health_check: failed to enqueue pg report email for result_id=%s",
                self.id,
            )

    @api.model
    def _get_pg_report_recipients(self):
        raw = self.env["ir.config_parameter"].sudo().get_param(
            "odoo_health_check.pg_report_emails", default="",
        ) or ""
        return [e.strip() for e in raw.split(",") if e.strip()]

    def _get_parsed_details(self):
        """Return details_json as a dict (empty dict if absent or invalid).
        Used by mail templates that need to iterate over the snapshot."""
        self.ensure_one()
        if not self.details_json:
            return {}
        try:
            return json.loads(self.details_json)
        except (ValueError, TypeError):
            return {}

    def _human_bytes(self, n):
        """Template helper: byte count -> '1.2 GB'."""
        return _human_bytes(n)

    def _human_delta_bytes(self, n):
        """Template helper: signed byte delta -> '+1.2 GB'."""
        return _human_delta_bytes(n)

    def _action_url(self):
        """Deep link into this record's form view via the appropriate
        act_window (Disk Checks for disk_*, PG Reports for pg_report).
        Used by mail templates for a 'View in Odoo' button."""
        self.ensure_one()
        base = self.get_base_url()
        xml_id = (
            "odoo_health_check.health_check_pg_report_action"
            if self.check_type == "pg_report"
            else "odoo_health_check.health_check_result_action"
        )
        action = self.env.ref(xml_id, raise_if_not_found=False)
        if not action:
            _logger.warning(
                "odoo_health_check: action %s missing, falling back to base URL", xml_id,
            )
            return base
        return f"{base}/odoo/action-{action.id}/{self.id}"
