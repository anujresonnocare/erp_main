from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResonnocareAttendancePolicy(models.Model):
    _name = "resonnocare.attendance.policy"
    _description = "Attendance Policy"
    _order = "priority asc, id asc"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    priority = fields.Integer(
        default=100,
        help="Lower number means higher precedence when matching employee policies.",
    )

    clinic_id = fields.Many2one(
        "resonnocare.clinic",
        string="Clinic",
        help="Leave empty to make this policy applicable across clinics.",
    )
    attendance_profile = fields.Selection(
        [("fixed", "Fixed"), ("roaming", "Roaming")],
        help="Leave empty to apply to both profiles.",
    )
    clinic_role = fields.Selection(
        [
            ("front_desk", "Front Desk"),
            ("doctor", "Audiologist"),
            ("technician", "Technician"),
            ("call_centre", "Call Centre"),
        ],
        help="Leave empty to apply to all clinic roles.",
    )

    late_tolerance_minutes = fields.Integer(default=15)
    free_late_per_month = fields.Integer(
        default=0,
        help="Number of late instances allowed in the month without penalty.",
    )
    apply_late_penalty = fields.Boolean(default=True)
    half_day_penalty_for_late = fields.Boolean(default=True)

    full_day_min_hours = fields.Float(default=8.0)
    half_day_min_hours = fields.Float(default=4.0)
    mandatory_break_minutes = fields.Integer(default=30)
    auto_deduct_break = fields.Boolean(default=True)

    auto_mark_absent_on_missing_punch = fields.Boolean(default=True)
    auto_create_lwp_for_absent = fields.Boolean(default=True)
    auto_create_half_day_deduction = fields.Boolean(default=True)

    compoff_validity_days = fields.Integer(default=30)
    attendance_cycle_close_day = fields.Integer(
        string="Attendance Cycle Close Day",
        default=25,
        help="Working day of month when attendance cycle is closed for payroll processing.",
    )
    salary_day = fields.Integer(
        string="Salary Day",
        default=1,
        help="Working day number of month used for payroll freeze trigger.",
    )
    payroll_cycle_note = fields.Char(
        string="Payroll Cycle Note",
        help="Optional note for payroll team (for example: cycle exceptions or freeze remarks).",
    )
    attendance_manual_url = fields.Char(
        string="Attendance Manual URL",
        help="Link shared with employees once attendance is activated.",
    )
    attendance_manual_note = fields.Text(
        string="Attendance Manual Note",
        default=(
            "Attendance is activated. Please follow the attendance app/user manual shared by HR."
        ),
    )

    def _validate_day_in_month(self, value, label):
        if value and (value < 1 or value > 31):
            raise ValidationError("%s must be between 1 and 31." % label)

    def _validate_cycle_days(self):
        for policy in self:
            policy._validate_day_in_month(policy.attendance_cycle_close_day, "Attendance Cycle Close Day")
            policy._validate_day_in_month(policy.salary_day, "Salary Day")

    @api.constrains("attendance_cycle_close_day", "salary_day")
    def _constrain_cycle_days(self):
        self._validate_cycle_days()

    def action_seed_default_policies(self):
        self.create_default_policies()

    @classmethod
    def _default_policy_values(cls):
        return [
            {
                "name": "HO Fixed - 3 Grace Lates",
                "priority": 10,
                "attendance_profile": "fixed",
                "clinic_role": "front_desk",
                "late_tolerance_minutes": 15,
                "free_late_per_month": 3,
            },
            {
                "name": "Clinic/Call Centre Fixed - Strict Late",
                "priority": 20,
                "attendance_profile": "fixed",
                "late_tolerance_minutes": 15,
                "free_late_per_month": 0,
            },
            {
                "name": "Roaming - No Late Penalty",
                "priority": 30,
                "attendance_profile": "roaming",
                "apply_late_penalty": False,
                "half_day_penalty_for_late": False,
                "free_late_per_month": 999,
            },
            {
                "name": "Global Default Policy",
                "priority": 999,
                "late_tolerance_minutes": 15,
                "free_late_per_month": 0,
            },
        ]

    def create_default_policies(self):
        if self.search_count([]):
            return
        self.create(self._default_policy_values())

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._validate_cycle_days()
        return records

    def write(self, vals):
        result = super().write(vals)
        if "attendance_cycle_close_day" in vals or "salary_day" in vals:
            self._validate_cycle_days()
        return result
