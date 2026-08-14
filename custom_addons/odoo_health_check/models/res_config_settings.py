from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    odoo_health_notify_emails = fields.Char(
        string="Cron Failure Notification Emails",
        config_parameter="odoo_health_check.notify_emails",
        help="Comma-separated list of recipients that receive an email "
             "every time a scheduled action fails. Leave empty to disable.",
    )
    odoo_health_retention_days = fields.Integer(
        string="History Retention (days)",
        config_parameter="odoo_health_check.retention_days",
        default=30,
        help="Cron execution history rows older than this are deleted daily. "
             "Set to 0 or negative to disable cleanup.",
    )
    odoo_health_disk_warn_pct = fields.Float(
        string="Disk Warning Threshold (%)",
        config_parameter="odoo_health_check.disk_warn_pct",
        default=80.0,
        digits=(5, 2),
        help="Disk usage above this percentage marks the result as 'warn'. "
             "Default: 80%. Must be lower than the critical threshold.",
    )
    odoo_health_disk_critical_pct = fields.Float(
        string="Disk Critical Threshold (%)",
        config_parameter="odoo_health_check.disk_critical_pct",
        default=90.0,
        digits=(5, 2),
        help="Disk usage above this percentage marks the result as 'critical'. "
             "Default: 90%. Must be higher than the warning threshold.",
    )
    odoo_health_disk_alert_emails = fields.Char(
        string="Disk Alert Emails",
        config_parameter="odoo_health_check.disk_alert_emails",
        help="Comma-separated recipients that receive an email when disk usage "
             "transitions from ok to warn or critical (or from warn to critical). "
             "One email per worsening transition - no per-hour spam. Leave empty to disable.",
    )
    odoo_health_pg_report_emails = fields.Char(
        string="PG Monthly Report Emails",
        config_parameter="odoo_health_check.pg_report_emails",
        help="Comma-separated recipients that receive the monthly PostgreSQL "
             "growth report on the 1st of each month at 08:00. Leave empty to disable email - the report row is still created.",
    )
