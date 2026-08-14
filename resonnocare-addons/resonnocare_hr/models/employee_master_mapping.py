from odoo import fields, models


class ResonnocareEmployeeMasterMapping(models.Model):
    _name = "resonnocare.employee.master.mapping"
    _description = "Resonnocare Employee Master Mapping"
    _rec_name = "employee_id"

    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        ondelete="cascade",
        index=True,
    )
    function_name = fields.Selection(
        [
            ("finance", "Finance"),
            ("hr", "HR"),
            ("it", "IT"),
            ("admin", "Admin"),
            ("marketing", "Marketing"),
            ("supply_chain", "Supply Chain"),
            ("operations", "Operations"),
            ("sales", "Sales"),
            ("other", "Other"),
        ],
        string="Function",
    )
    region_id = fields.Many2one("res.country.group", string="Region")
    weekly_off_pattern = fields.Selection(
        [
            ("sun", "Sunday"),
            ("sat_sun", "Saturday + Sunday"),
            ("rotational", "Rotational"),
            ("none", "No Fixed Weekly Off"),
        ],
        string="Weekly Off Pattern",
        default="sun",
    )
    holiday_calendar_id = fields.Many2one(
        "resonnocare.holiday.calendar",
        string="Holiday Calendar Mapping",
    )

    _sql_constraints = [
        (
            "employee_unique_mapping",
            "unique(employee_id)",
            "Only one employee master mapping record is allowed per employee.",
        )
    ]
