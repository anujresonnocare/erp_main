from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    clinic_id = fields.Many2one(
        "resonnocare.clinic",
        string="Assigned Clinic",
        help="The clinic where this employee works",
        tracking=True,
    )

    clinic_role = fields.Selection(
        [
            ("front_desk", "Front Desk"),
            ("doctor", "Audiologist"),
            ("technician", "Technician"),
            ("call_centre", "Call Centre"),
        ],
        string="Clinic Role",
        tracking=True,
        help="Role within the clinic (distinct from Job Position)",
    )

    @api.model
    def default_get(self, fields):
        res = super(HrEmployee, self).default_get(fields)
        if "clinic_id" in fields and not res.get("clinic_id"):
            res["clinic_id"] = self.env.user.employee_id.clinic_id.id
        return res

    shift_timing = fields.Char(
        string="Shift Timing",
        help="e.g. 9 AM - 5 PM",
    )
