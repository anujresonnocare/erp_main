# -*- coding: utf-8 -*-
from odoo import fields, models


class ServiaSafetyInspection(models.Model):
    _name = 'servia.safety.inspection'
    _description = 'Safety Inspection Checklist'
    _order = 'inspect_date desc'

    name = fields.Char('Inspection Title', required=True)
    area = fields.Char('Area / Location')
    inspector = fields.Char('Inspector')
    inspect_date = fields.Date('Date', default=fields.Date.context_today)
    result = fields.Selection([
        ('pass', 'Pass'), ('fail', 'Fail'), ('na', 'N/A'),
    ], string='Result', default='pass')
    risk = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'),
    ], string='Risk Level', default='low')
    action_by = fields.Char('Action Owner')
    findings = fields.Text('Findings / Actions')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], default='draft')
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.user.company_id)

    def action_confirm(self):
        for rec in self:
            rec.write({'state': 'confirmed'})

    def action_reset(self):
        for rec in self:
            rec.write({'state': 'draft'})
