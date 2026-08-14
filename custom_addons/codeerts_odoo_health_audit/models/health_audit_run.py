from odoo import fields, models


class HealthAuditRun(models.Model):
    _name = 'health.audit.run'
    _description = 'Health Audit Run'
    _order = 'create_date desc'

    name = fields.Char(
        default=lambda self: fields.Datetime.to_string(fields.Datetime.now()))
    trigger = fields.Selection(
        [('manual', 'Manual'), ('scheduled', 'Scheduled')], default='manual')
    overall_score = fields.Integer()
    score_finance = fields.Integer()
    score_sales = fields.Integer()
    score_inventory = fields.Integer()
    score_data_quality = fields.Integer()
    score_security = fields.Integer()
    count_critical = fields.Integer()
    count_warning = fields.Integer()
    count_info = fields.Integer()
    duration = fields.Float(help="Seconds")
    scanned_app_count = fields.Integer(help="Number of installed apps audited.")
    active_check_count = fields.Integer(help="Number of checks executed.")
    finding_ids = fields.One2many('health.audit.finding', 'run_id')
