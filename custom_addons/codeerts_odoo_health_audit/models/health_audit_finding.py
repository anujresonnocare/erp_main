from odoo import fields, models
from odoo.tools.safe_eval import safe_eval

from .health_check import SEVERITY


class HealthAuditFinding(models.Model):
    _name = 'health.audit.finding'
    _description = 'Health Audit Finding'

    run_id = fields.Many2one('health.audit.run', required=True, ondelete='cascade')
    check_id = fields.Many2one('health.check', required=True, ondelete='restrict')
    category = fields.Selection(related='check_id.category', store=True)
    severity = fields.Selection(SEVERITY)
    count = fields.Integer()
    affected_model = fields.Char()
    domain = fields.Char(help="Stored domain string for the View Records action.")

    def action_view_records(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.affected_model,
            'domain': safe_eval(self.domain or '[]'),
            'views': [(False, 'list'), (False, 'form')],
            'view_mode': 'list,form',
            'name': self.check_id.name,
            'target': 'current',
        }
