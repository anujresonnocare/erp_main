from odoo import _, fields, models


class ResonnocareUatChecklist(models.Model):
    _name = "resonnocare.uat.checklist"
    _description = "Resonnocare UAT Checklist"
    _order = "employee_id, sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    employee_id = fields.Many2one("hr.employee", required=True, ondelete="cascade")
    owner_user_id = fields.Many2one("res.users", string="Owner")
    area = fields.Selection(
        [
            ("onboarding", "Onboarding"),
            ("attendance", "Attendance"),
            ("leave", "Leave"),
            ("payroll", "Payroll"),
            ("integration", "Integration"),
        ],
        required=True,
        default="onboarding",
    )
    status = fields.Selection(
        [
            ("pending", "Pending"),
            ("passed", "Passed"),
            ("failed", "Failed"),
        ],
        default="pending",
        required=True,
    )
    tested_on = fields.Datetime(readonly=True, copy=False)
    note = fields.Text()

    def action_mark_passed(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.write({"status": "passed", "tested_on": now})
        return True

    def action_mark_failed(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.write({"status": "failed", "tested_on": now})
        return True
