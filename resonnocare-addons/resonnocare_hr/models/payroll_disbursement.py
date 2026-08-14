import base64
import csv
import io
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResonnocarePayrollDisbursement(models.Model):
    _name = "resonnocare.payroll.disbursement"
    _description = "Payroll Disbursement Batch"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "pay_month desc, id desc"

    name = fields.Char(
        string="Batch",
        required=True,
        default=lambda self: _("New"),
        copy=False,
    )
    pay_month = fields.Date(
        string="Pay Month",
        required=True,
        default=lambda self: fields.Date.today().replace(day=1),
    )
    salary_date = fields.Date(
        string="Salary Date",
        required=True,
        default=lambda self: fields.Date.today().replace(day=1),
    )
    state = fields.Selection(
        [("draft", "Draft"), ("frozen", "Frozen"), ("disbursed", "Disbursed")],
        default="draft",
        tracking=True,
    )
    line_ids = fields.One2many(
        "resonnocare.payroll.disbursement.line",
        "batch_id",
        string="Employees",
    )
    total_employees = fields.Integer(compute="_compute_totals")
    total_net_amount = fields.Float(compute="_compute_totals")
    bank_export_file = fields.Binary(string="Bank File", readonly=True, attachment=True)
    bank_export_filename = fields.Char(string="Bank Filename", readonly=True)

    @api.depends("line_ids.net_amount")
    def _compute_totals(self):
        for rec in self:
            rec.total_employees = len(rec.line_ids)
            rec.total_net_amount = sum(rec.line_ids.mapped("net_amount"))

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = seq.next_by_code("resonnocare.payroll.disbursement") or _("New")
        return super().create(vals_list)

    @staticmethod
    def _month_bounds(anchor):
        first_day = anchor.replace(day=1)
        next_month = (first_day + timedelta(days=32)).replace(day=1)
        last_day = next_month - timedelta(days=1)
        return first_day, last_day

    @staticmethod
    def _net_amount(slip):
        if "net_wage" in slip._fields:
            return slip.net_wage or 0.0
        net_line = slip.line_ids.filtered(lambda l: (l.code or "").upper() == "NET")[:1]
        if net_line:
            if "total" in net_line._fields:
                return net_line.total or 0.0
            if "amount" in net_line._fields:
                return net_line.amount or 0.0
        return 0.0

    def action_fetch_payslips(self):
        for rec in self:
            month_from, month_to = self._month_bounds(rec.pay_month)
            slips = self.env["hr.payslip"].sudo().search(
                [
                    ("date_from", "<=", month_to),
                    ("date_to", ">=", month_from),
                    ("state", "in", ["done", "paid"]),
                ]
            )
            lines = []
            for slip in slips:
                employee = slip.employee_id
                is_resigned = False
                if "departure_date" in employee._fields and employee.departure_date:
                    is_resigned = True
                elif "active" in employee._fields and not employee.active:
                    is_resigned = True
                lines.append(
                    (
                        0,
                        0,
                        {
                            "employee_id": employee.id,
                            "payslip_id": slip.id,
                            "net_amount": self._net_amount(slip),
                            "is_resigned": is_resigned,
                        },
                    )
                )
            rec.line_ids.unlink()
            rec.write({"line_ids": lines})

    def action_freeze(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_("No employees in batch. Click Fetch Payslips first."))
            rec.state = "frozen"

    def action_disburse(self):
        for rec in self:
            if rec.state != "frozen":
                raise UserError(_("Freeze the batch before disbursement."))
            rec.state = "disbursed"

    def action_export_bank_file(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("No payout lines available for export."))
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Employee", "Bank Account", "IFSC", "Net Amount", "Resigned"])
        for line in self.line_ids:
            bank_acc = ""
            ifsc = ""
            emp = line.employee_id
            if "bank_account_id" in emp._fields and emp.bank_account_id:
                bank_acc = emp.bank_account_id.acc_number or ""
                ifsc = emp.bank_account_id.bank_id.bic or ""
            writer.writerow(
                [
                    emp.name or "",
                    bank_acc,
                    ifsc,
                    "%.2f" % (line.net_amount or 0.0),
                    "YES" if line.is_resigned else "NO",
                ]
            )
        content = output.getvalue().encode()
        output.close()
        file_name = "bank_disbursement_%s.csv" % fields.Date.to_string(self.pay_month)
        self.write(
            {
                "bank_export_file": base64.b64encode(content),
                "bank_export_filename": file_name,
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/?model=resonnocare.payroll.disbursement&id=%s&field=bank_export_file&filename_field=bank_export_filename&download=true"
            % self.id,
            "target": "self",
        }


class ResonnocarePayrollDisbursementLine(models.Model):
    _name = "resonnocare.payroll.disbursement.line"
    _description = "Payroll Disbursement Line"
    _order = "id asc"

    batch_id = fields.Many2one("resonnocare.payroll.disbursement", required=True, ondelete="cascade")
    employee_id = fields.Many2one("hr.employee", string="Employee", required=True, readonly=True)
    payslip_id = fields.Many2one("hr.payslip", string="Payslip", required=True, readonly=True)
    net_amount = fields.Float(string="Net Amount", readonly=True)
    is_resigned = fields.Boolean(string="Resigned", readonly=True)

