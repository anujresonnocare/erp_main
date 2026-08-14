import json
from datetime import timedelta

from odoo import api, fields, models

from .health_check_result import _human_bytes, _human_delta_bytes


class HealthCheckDashboard(models.Model):
    """Singleton dashboard summarising cron health, disk usage, and the
    latest PostgreSQL growth report.

    Backed by a single record (xmlid `dashboard_singleton`) whose data
    fields are all `compute=, store=False`, so every read recomputes
    against the underlying tables. Refresh = re-open the same record.
    No transient row churn, no stored snapshot to invalidate.
    """

    _name = "health.check.dashboard"
    _description = "Odoo Health Check Dashboard"
    _rec_name = "name"

    name = fields.Char(
        default="Dashboard",
        readonly=True,
    )

    failures_24h = fields.Integer(
        string="Cron failures (24h)",
        compute="_compute_dashboard",
    )
    failures_7d = fields.Integer(
        string="Cron failures (7d)",
        compute="_compute_dashboard",
    )
    history_total_7d = fields.Integer(
        string="Cron runs (7d)",
        compute="_compute_dashboard",
    )

    disk_root_status = fields.Selection(
        [("ok", "OK"), ("warn", "Warning"), ("critical", "Critical"),
         ("error", "Error"), ("unknown", "No data yet")],
        compute="_compute_dashboard",
    )
    disk_root_used_pct = fields.Float(
        compute="_compute_dashboard",
        digits=(5, 2),
    )
    disk_root_summary = fields.Char(
        compute="_compute_dashboard",
    )
    disk_root_at = fields.Datetime(
        string="Last disk:root sample",
        compute="_compute_dashboard",
    )

    disk_filestore_status = fields.Selection(
        [("ok", "OK"), ("warn", "Warning"), ("critical", "Critical"),
         ("error", "Error"), ("unknown", "No data yet")],
        compute="_compute_dashboard",
    )
    disk_filestore_used_pct = fields.Float(
        compute="_compute_dashboard",
        digits=(5, 2),
    )
    disk_filestore_summary = fields.Char(
        compute="_compute_dashboard",
    )
    disk_filestore_at = fields.Datetime(
        string="Last filestore sample",
        compute="_compute_dashboard",
    )

    last_pg_report_at = fields.Datetime(
        string="Last PG report",
        compute="_compute_dashboard",
    )
    last_pg_report_db_size = fields.Char(
        string="DB size",
        compute="_compute_dashboard",
    )
    last_pg_report_db_delta = fields.Char(
        string="DB delta vs previous",
        compute="_compute_dashboard",
    )
    last_pg_report_table = fields.Char(
        string="Largest table",
        compute="_compute_dashboard",
    )

    # No @api.depends on purpose: inputs live in other models. With
    # store=False the ORM recomputes on every field access, so opening
    # or refreshing the form view always reads fresh data.
    def _compute_dashboard(self):
        for rec in self:
            snapshot = rec._compute_dashboard_snapshot()
            for key, value in snapshot.items():
                rec[key] = value

    @api.model
    def _compute_dashboard_snapshot(self):
        return {
            **self._compute_cron_health(),
            **self._compute_disk_tile("disk_root", "disk_root"),
            **self._compute_disk_tile("disk_filestore", "disk_filestore"),
            **self._compute_pg_report_tile(),
        }

    @api.model
    def _compute_cron_health(self):
        History = self.env["ir.cron.history"]
        now = fields.Datetime.now()
        return {
            "failures_24h": History.search_count([
                ("state", "=", "failed"),
                ("date_start", ">=", now - timedelta(days=1)),
            ]),
            "failures_7d": History.search_count([
                ("state", "=", "failed"),
                ("date_start", ">=", now - timedelta(days=7)),
            ]),
            "history_total_7d": History.search_count([
                ("date_start", ">=", now - timedelta(days=7)),
            ]),
        }

    @api.model
    def _compute_disk_tile(self, check_type, prefix):
        """Read the latest health.check.result row of the given check_type
        and return a dict with `<prefix>_status / _used_pct / _summary / _at`.
        Returns 'unknown' status with empty summary if no row exists yet."""
        row = self.env["health.check.result"].search(
            [("check_type", "=", check_type)],
            order="date desc, id desc",
            limit=1,
        )
        if not row:
            return {
                f"{prefix}_status": "unknown",
                f"{prefix}_used_pct": 0.0,
                f"{prefix}_summary": "No samples yet - the hourly disk cron will populate this.",
                f"{prefix}_at": False,
            }
        if row.status == "error":
            return {
                f"{prefix}_status": "error",
                f"{prefix}_used_pct": 0.0,
                f"{prefix}_summary": (row.mount_path or "") + " - last sample raised an error",
                f"{prefix}_at": row.date,
            }
        return {
            f"{prefix}_status": row.status,
            f"{prefix}_used_pct": row.used_pct or 0.0,
            f"{prefix}_summary": (
                f"{row.mount_path or '?'}: "
                f"{_human_bytes(row.free_bytes)} free of {_human_bytes(row.total_bytes)}"
            ),
            f"{prefix}_at": row.date,
        }

    @api.model
    def _compute_pg_report_tile(self):
        row = self.env["health.check.result"].search(
            [("check_type", "=", "pg_report"), ("status", "=", "ok")],
            order="date desc, id desc",
            limit=1,
        )
        if not row:
            return {
                "last_pg_report_at": False,
                "last_pg_report_db_size": "",
                "last_pg_report_db_delta": "Not generated yet (runs 1st of each month at 08:00).",
                "last_pg_report_table": "",
            }
        try:
            data = json.loads(row.details_json) if row.details_json else {}
        except (ValueError, TypeError):
            data = {}
        tables = data.get("tables") or []
        top = tables[0] if tables else None
        delta = data.get("total_db_bytes_delta")
        return {
            "last_pg_report_at": row.date,
            "last_pg_report_db_size": _human_bytes(data.get("total_db_bytes")),
            "last_pg_report_db_delta": (
                _human_delta_bytes(delta) + " vs previous report"
                if delta is not None
                else "First report (no previous to compare)."
            ),
            "last_pg_report_table": (
                f"{top['name']} - {_human_bytes(top.get('total_bytes', 0))}"
                if top
                else ""
            ),
        }

    @api.model
    def _get_singleton(self):
        """Return the singleton dashboard record. Created on install via
        data XML; this fallback creates it on the fly if a manual unlink
        somehow removed it."""
        rec = self.env.ref(
            "odoo_health_check.dashboard_singleton", raise_if_not_found=False,
        )
        if rec:
            return rec
        return self.sudo().create({"name": "Dashboard"})

    @api.model
    def action_open(self):
        """Server-action entry point: open the singleton dashboard.
        Form view rendering triggers the compute fields."""
        return self._dashboard_action(self._get_singleton().id)

    def action_refresh(self):
        """Re-open the singleton. Form reload re-reads the compute
        fields, which always recompute against current data."""
        return self._dashboard_action(self._get_singleton().id)

    @api.model
    def _dashboard_action(self, res_id):
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "form",
            "view_id": self.env.ref(
                "odoo_health_check.health_check_dashboard_view_form"
            ).id,
            "res_id": res_id,
            "target": "main",
            "name": "Health Check Dashboard",
        }
