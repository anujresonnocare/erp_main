# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models, _

class HREmployee(models.Model):
    _inherit = 'hr.employee'
    _description = 'Employee'

    medical_examination_ids = fields.One2many("hr.employee.medical.examination", "employee_id", string='Medical Examination')
    medical_examination_count = fields.Integer('Total Examination', compute="_compute_medical_examination_count")

    @api.depends("medical_examination_ids")
    def _compute_medical_examination_count(self):
        for record in self:
            record.medical_examination_count = len(record.medical_examination_ids)
