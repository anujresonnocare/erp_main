import logging
import socket
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class IrCronHistory(models.Model):
    _name = "ir.cron.history"
    _description = "Cron Execution History"
    _order = "date_start desc"
    _rec_name = "cron_id"

    cron_id = fields.Many2one(
        "ir.cron",
        string="Scheduled Action",
        required=True,
        ondelete="cascade",
        index=True,
    )
    date_start = fields.Datetime(
        string="Started",
        required=True,
        default=fields.Datetime.now,
        index=True,
    )
    date_end = fields.Datetime(
        string="Ended",
    )
    duration_sec = fields.Float(
        string="Duration (s)",
        digits=(12, 3),
        compute="_compute_duration_sec",
        store=True,
        help="date_end - date_start in seconds. NULL while the run is in flight.",
    )
    state = fields.Selection(
        [
            ("running", "Running"),
            ("success", "Success"),
            ("failed", "Failed"),
        ],
        required=True,
        default="running",
        index=True,
    )
    error_traceback = fields.Text(
        string="Error Traceback",
    )
    server_name = fields.Char(
        string="Server",
        default=lambda _: socket.gethostname(),
        readonly=True,
    )

    _sql_constraints = [
        (
            "date_order",
            "CHECK (date_end IS NULL OR date_end >= date_start)",
            "End time must be on or after start time.",
        ),
    ]

    @api.depends("date_start", "date_end")
    def _compute_duration_sec(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                rec.duration_sec = (rec.date_end - rec.date_start).total_seconds()
            else:
                rec.duration_sec = 0.0

    @api.model
    def _cron_cleanup_history(self, batch_size=5000):
        """Delete history rows older than the configured retention window.

        Retention days comes from `odoo_health_check.retention_days`
        (default 30). A non-positive value disables cleanup.
        """
        param = self.env["ir.config_parameter"].sudo().get_param(
            "odoo_health_check.retention_days", default="30",
        )
        if not param.isdigit():
            raise UserError("Invalid retention days")
        retention = int(param)
        cutoff = fields.Datetime.now() - timedelta(days=retention)
        to_delete = self.search(
            [("date_start", "<", cutoff)], limit=batch_size, order="date_start asc",
        )
        count = len(to_delete)
        if count:
            to_delete.unlink()
            _logger.info(
                "odoo_health_check: retention cleanup removed %d rows older than %s "
                "(retention=%d days)",
                count, cutoff, retention,
            )
        return count

    def _action_url(self):
        """Deep link into this record's form view via the Cron History
        act_window. Used by mail templates for a 'View in Odoo' button.
        Falls back to the base URL if the action ref is missing."""
        self.ensure_one()
        base = self.get_base_url()
        action = self.env.ref(
            "odoo_health_check.ir_cron_history_action", raise_if_not_found=False,
        )
        if not action:
            _logger.warning(
                "odoo_health_check: action ir_cron_history_action missing, "
                "falling back to base URL",
            )
            return base
        return f"{base}/odoo/action-{action.id}/{self.id}"
