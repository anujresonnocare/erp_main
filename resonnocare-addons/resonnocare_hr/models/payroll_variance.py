from datetime import date, timedelta

from odoo import api, fields, models


class ResonnocarePayrollVarianceWizard(models.TransientModel):
    _name = "resonnocare.payroll.variance.wizard"
    _description = "Payroll Variance Wizard"

    month = fields.Date(
        string="Payroll Month",
        required=True,
        default=lambda self: fields.Date.today().replace(day=1),
        help="Pick any date in the month to compare.",
    )
    threshold_percent = fields.Float(string="Variance Threshold %", default=10.0)
    line_ids = fields.One2many(
        "resonnocare.payroll.variance.wizard.line",
        "wizard_id",
        string="Variance Lines",
    )

    @staticmethod
    def _month_bounds(anchor):
        first_day = anchor.replace(day=1)
        next_month = (first_day + timedelta(days=32)).replace(day=1)
        last_day = next_month - timedelta(days=1)
        prev_last = first_day - timedelta(days=1)
        prev_first = prev_last.replace(day=1)
        return first_day, last_day, prev_first, prev_last

    @staticmethod
    def _net_amount(slip):
        if "net_wage" in slip._fields:
            return slip.net_wage or 0.0
        if "line_ids" in slip._fields:
            net_line = slip.line_ids.filtered(lambda l: (l.code or "").upper() == "NET")[:1]
            if net_line:
                if "total" in net_line._fields:
                    return net_line.total or 0.0
                if "amount" in net_line._fields:
                    return net_line.amount or 0.0
        return 0.0

    def action_generate(self):
        for wizard in self:
            wizard.line_ids.unlink()
            cur_from, cur_to, prev_from, prev_to = self._month_bounds(wizard.month)
            slip_model = self.env["hr.payslip"].sudo()
            cur_slips = slip_model.search(
                [("date_from", "<=", cur_to), ("date_to", ">=", cur_from), ("state", "in", ["done", "paid"])]
            )
            prev_slips = slip_model.search(
                [("date_from", "<=", prev_to), ("date_to", ">=", prev_from), ("state", "in", ["done", "paid"])]
            )
            prev_map = {s.employee_id.id: self._net_amount(s) for s in prev_slips}
            rows = []
            for slip in cur_slips:
                current = self._net_amount(slip)
                previous = prev_map.get(slip.employee_id.id, 0.0)
                variance = current - previous
                variance_pct = (variance / previous * 100.0) if previous else (100.0 if current else 0.0)
                rows.append(
                    (
                        0,
                        0,
                        {
                            "employee_id": slip.employee_id.id,
                            "current_net": current,
                            "previous_net": previous,
                            "variance_amount": variance,
                            "variance_percent": variance_pct,
                            "is_alert": abs(variance_pct) >= (wizard.threshold_percent or 0.0),
                        },
                    )
                )
            wizard.write({"line_ids": rows})
        return {
            "type": "ir.actions.act_window",
            "name": "Payroll Variance Report",
            "res_model": "resonnocare.payroll.variance.wizard",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }


class ResonnocarePayrollVarianceWizardLine(models.TransientModel):
    _name = "resonnocare.payroll.variance.wizard.line"
    _description = "Payroll Variance Wizard Line"
    _order = "variance_percent desc, id desc"

    wizard_id = fields.Many2one("resonnocare.payroll.variance.wizard", required=True, ondelete="cascade")
    employee_id = fields.Many2one("hr.employee", string="Employee", readonly=True)
    current_net = fields.Float(string="Current Month Net", readonly=True)
    previous_net = fields.Float(string="Previous Month Net", readonly=True)
    variance_amount = fields.Float(string="Variance Amount", readonly=True)
    variance_percent = fields.Float(string="Variance %", readonly=True)
    is_alert = fields.Boolean(string="Needs Review", readonly=True)

