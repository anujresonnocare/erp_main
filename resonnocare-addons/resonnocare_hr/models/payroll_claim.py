from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResonnocarePayrollClaim(models.Model):
    _name = "resonnocare.payroll.claim"
    _description = "Payroll Reimbursement Claim"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "claim_date desc, id desc"

    name = fields.Char(
        string="Claim Reference",
        required=True,
        copy=False,
        default=lambda self: _("New"),
        tracking=True,
    )
    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        required=True,
        default=lambda self: self.env.user.employee_id.id,
        tracking=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Employee User",
        related="employee_id.user_id",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company.id,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )
    claim_date = fields.Date(
        string="Claim Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    claim_type = fields.Selection(
        [
            ("travel", "Travel"),
            ("medical", "Medical"),
            ("communication", "Communication"),
            ("food", "Food"),
            ("other", "Other"),
        ],
        string="Claim Type",
        required=True,
        default="other",
        tracking=True,
    )
    amount_requested = fields.Monetary(
        string="Requested Amount",
        required=True,
        tracking=True,
    )
    amount_approved = fields.Monetary(
        string="Approved Amount",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("query", "Query Raised"),
            ("hr_approved", "HR Approved"),
            ("hr_rejected", "HR Rejected"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )
    submitted_on = fields.Datetime(string="Submitted On", readonly=True, copy=False)
    reviewed_on = fields.Datetime(string="Reviewed On", readonly=True, copy=False)
    reviewed_by_id = fields.Many2one("res.users", string="Reviewed By", readonly=True, copy=False)
    notes = fields.Text(string="Notes")
    hr_remarks = fields.Text(string="HR Remarks")
    is_tax_exempt = fields.Boolean(
        string="Tax Exempt",
        default=True,
        help="Approved amount moves to tax-exempt earnings bucket in payroll.",
    )
    payslip_id = fields.Many2one(
        "hr.payslip",
        string="Settled In Payslip",
        readonly=True,
        copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = seq.next_by_code("resonnocare.payroll.claim") or _("New")
            if not vals.get("amount_approved"):
                vals["amount_approved"] = vals.get("amount_requested", 0.0)
        return super().create(vals_list)

    def write(self, vals):
        if "amount_requested" in vals and "amount_approved" not in vals:
            for claim in self:
                if claim.state in ("draft", "submitted", "query"):
                    vals = dict(vals, amount_approved=vals["amount_requested"])
                    break
        return super().write(vals)

    def _check_employee_owner(self):
        for claim in self:
            if claim.employee_id.user_id != self.env.user and not self.env.user.has_group(
                "resonnocare_base.group_resonnocare_hr"
            ) and not self.env.user.has_group("resonnocare_base.group_resonnocare_super_admin"):
                raise UserError(_("You can manage only your own payroll claims."))

    def action_submit(self):
        self._check_employee_owner()
        for claim in self:
            if claim.state not in ("draft", "query"):
                continue
            if claim.amount_requested <= 0:
                raise UserError(_("Requested amount must be greater than zero."))
            claim.write(
                {
                    "state": "submitted",
                    "submitted_on": fields.Datetime.now(),
                    "amount_approved": claim.amount_requested,
                }
            )

    def action_mark_query(self):
        self._check_hr_access()
        self.write(
            {
                "state": "query",
                "reviewed_on": fields.Datetime.now(),
                "reviewed_by_id": self.env.user.id,
            }
        )

    def action_hr_approve(self):
        self._check_hr_access()
        for claim in self:
            approved = claim.amount_approved or 0.0
            if approved <= 0:
                raise UserError(_("Approved amount must be greater than zero."))
            claim.write(
                {
                    "state": "hr_approved",
                    "reviewed_on": fields.Datetime.now(),
                    "reviewed_by_id": self.env.user.id,
                }
            )

    def action_hr_reject(self):
        self._check_hr_access()
        self.write(
            {
                "state": "hr_rejected",
                "reviewed_on": fields.Datetime.now(),
                "reviewed_by_id": self.env.user.id,
                "amount_approved": 0.0,
            }
        )

    def action_reset_draft(self):
        self._check_hr_access()
        self.write(
            {
                "state": "draft",
                "reviewed_on": False,
                "reviewed_by_id": False,
                "hr_remarks": False,
            }
        )

    def _check_hr_access(self):
        if not (
            self.env.user.has_group("resonnocare_base.group_resonnocare_hr")
            or self.env.user.has_group("resonnocare_base.group_resonnocare_super_admin")
        ):
            raise UserError(_("Only HR/Admin can perform this action."))

