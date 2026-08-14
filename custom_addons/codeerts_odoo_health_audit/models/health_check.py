from odoo import api, fields, models
from odoo.exceptions import ValidationError

SEVERITY = [('info', 'Info'), ('warning', 'Warning'), ('critical', 'Critical')]
CATEGORY = [
    ('finance', 'Finance'), ('sales', 'Sales'), ('inventory', 'Inventory'),
    ('data_quality', 'Data Quality'), ('security', 'Security'),
]


class HealthCheck(models.Model):
    _name = 'health.check'
    _description = 'Odoo Health Check'
    _order = 'category, name'

    name = fields.Char(required=True)
    category = fields.Selection(CATEGORY, required=True)
    module_dependency = fields.Char(
        required=True,
        help="Technical name of the Odoo module this check needs installed.")
    method_name = fields.Char(
        required=True, help="Engine method that runs this check.")
    default_severity = fields.Selection(SEVERITY, required=True, default='warning')
    active = fields.Boolean(default=True)
    description = fields.Text()
    why_it_matters = fields.Text()
    param_ids = fields.One2many('health.check.param', 'check_id')

    def get_param(self, key, cast=int):
        self.ensure_one()
        p = self.param_ids.filtered(lambda r: r.key == key)
        return cast(p.value) if p else None


class HealthCheckParam(models.Model):
    _name = 'health.check.param'
    _description = 'Health Check Parameter'

    check_id = fields.Many2one('health.check', required=True, ondelete='cascade')
    key = fields.Char(required=True)
    label = fields.Char(required=True)
    help = fields.Char()
    ptype = fields.Selection(
        [('int', 'Integer'), ('float', 'Float'), ('bool', 'Boolean'), ('char', 'Text')],
        required=True, default='int')
    value = fields.Char(required=True)
    default = fields.Char(required=True)
    min_val = fields.Float()
    max_val = fields.Float()

    @api.constrains('value', 'min_val', 'max_val', 'ptype')
    def _check_bounds(self):
        for rec in self:
            if rec.ptype in ('int', 'float'):
                try:
                    v = float(rec.value)
                except ValueError:
                    raise ValidationError("%s must be a number." % rec.label)
                if rec.min_val and v < rec.min_val:
                    raise ValidationError("%s cannot be below %s." % (rec.label, rec.min_val))
                if rec.max_val and v > rec.max_val:
                    raise ValidationError("%s cannot be above %s." % (rec.label, rec.max_val))

    def reset_to_default(self):
        for rec in self:
            rec.value = rec.default
