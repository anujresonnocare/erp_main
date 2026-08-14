from odoo import models, fields

class HrDepartment(models.Model):
    _inherit = "hr.department"

    clinic_id = fields.Many2one(
        "resonnocare.clinic",
        string="Clinic",
        help="The clinic this department belongs to"
    )
