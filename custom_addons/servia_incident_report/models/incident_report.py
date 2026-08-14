# -*- coding: utf-8 -*-
from odoo import fields, models


class ServiaIncidentReport(models.Model):
    _name = 'servia.incident.report'
    _description = 'HSE Incident Report'
    _order = 'date desc'
    _rec_name = 'name'

    name = fields.Char('Title', required=True)
    date = fields.Date('Date', default=fields.Date.context_today)
    location = fields.Char('Location')
    severity = fields.Selection([
        ('minor', 'Minor'),
        ('moderate', 'Moderate'),
        ('major', 'Major'),
    ], default='minor')
    reported_by = fields.Many2one('res.users', string='Reported By',
                                  default=lambda self: self.env.user)
    description = fields.Text('Description')
    action_taken = fields.Text('Action Taken')
    state = fields.Selection([
        ('open', 'Open'),
        ('investigating', 'Investigating'),
        ('closed', 'Closed'),
    ], default='open')
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.user.company_id)

    def action_investigate(self):
        for rec in self:
            rec.write({'state': 'investigating'})

    def action_close(self):
        for rec in self:
            rec.write({'state': 'closed'})

    def action_reopen(self):
        for rec in self:
            rec.write({'state': 'open'})
