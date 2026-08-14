from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class ResonnocareAdvanceApprovalRequest(models.Model):
    _name = "resonnocare.advance.approval.request"
    _description = "Minimum Advance Approval Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Request ID",
        required=True,
        copy=False,
        default=lambda self: "New",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )

    sale_order_id = fields.Many2one(
        "sale.order", string="Sale Order", required=True, ondelete="cascade", tracking=True
    )
    # Backward-compatibility field: non-stored so no DB column is required.
    # This avoids crashes from older/cached views referencing `appointment_id`.
    appointment_id = fields.Char(
        string="Appointment",
        compute="_compute_appointment_id_compat",
        readonly=True,
    )
    clinic_id = fields.Many2one(
        "resonnocare.clinic",
        string="Clinic",
        related="sale_order_id.clinic_id",
        store=True,
        readonly=True,
    )
    patient_id = fields.Many2one(
        "res.partner",
        string="Patient",
        related="sale_order_id.patient_id",
        store=True,
        readonly=True,
    )
    patient_code = fields.Char(
        string="Patient ID",
        related="patient_id.patient_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="sale_order_id.currency_id",
        readonly=True,
    )

    sale_order_total = fields.Monetary(
        string="Sale Order Total",
        related="sale_order_id.amount_total",
        store=True,
        readonly=True,
    )
    min_advance_required = fields.Monetary(
        string="Minimum Advance Required (30%)",
        compute="_compute_min_advance_metrics",
        store=True,
        readonly=True,
    )
    amount_paid = fields.Monetary(
        string="Amount Already Paid",
        compute="_compute_min_advance_metrics",
        store=True,
        readonly=True,
    )
    requested_min_advance = fields.Monetary(
        string="Requested Minimum Advance",
        tracking=True,
        help="Approved threshold required before fitting appointment can be created.",
    )
    shortfall_vs_30 = fields.Monetary(
        string="Shortfall vs 30%",
        compute="_compute_min_advance_metrics",
        store=True,
        readonly=True,
    )

    reason = fields.Text(string="Reason")
    requested_by_id = fields.Many2one(
        "res.users",
        string="Requested By",
        default=lambda self: self.env.user,
        readonly=True,
    )
    approved_by_id = fields.Many2one("res.users", string="Approved By", readonly=True)
    approved_on = fields.Datetime(string="Approved On", readonly=True)
    rejection_reason = fields.Text(string="Rejection Reason")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code(
                        "resonnocare.advance.approval.request"
                    )
                    or "New"
                )
            if vals.get("sale_order_id") and not vals.get("requested_min_advance"):
                sale = self.env["sale.order"].browse(vals["sale_order_id"])
                vals["requested_min_advance"] = (sale.amount_total or 0.0) * 0.30
        return super().create(vals_list)

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        sale_order_id = vals.get("sale_order_id") or self.env.context.get("default_sale_order_id")
        if sale_order_id and "requested_min_advance" in fields_list:
            sale = self.env["sale.order"].browse(sale_order_id)
            vals.setdefault("requested_min_advance", (sale.amount_total or 0.0) * 0.30)
        return vals

    @api.depends("sale_order_id", "sale_order_id.amount_total", "sale_order_id.invoice_ids.amount_residual", "sale_order_id.invoice_ids.amount_total", "sale_order_id.invoice_ids.state")
    def _compute_min_advance_metrics(self):
        for rec in self:
            sale = rec.sale_order_id.sudo()
            total = sale.amount_total or 0.0
            min_required = total * 0.30
            posted_invoices = rec._get_related_customer_invoices_for_sale(sale).filtered(
                lambda inv: inv.state == "posted"
            )
            paid = 0.0
            for inv in posted_invoices:
                if hasattr(inv, "_get_contract_advance_paid"):
                    paid += inv._get_contract_advance_paid() or 0.0
                else:
                    paid += (inv.amount_total or 0.0) - (inv.amount_residual or 0.0)
            rec.min_advance_required = min_required
            rec.amount_paid = paid
            rec.shortfall_vs_30 = max(min_required - paid, 0.0)

    def _compute_appointment_id_compat(self):
        for rec in self:
            rec.appointment_id = False

    def _get_related_customer_invoices_for_sale(self, sale):
        self.ensure_one()
        sale_sudo = sale.sudo()
        invoice_model = self.env["account.move"].sudo()

        invoices = sale_sudo.invoice_ids.filtered(
            lambda inv: inv.move_type == "out_invoice" and inv.state != "cancel"
        )
        invoices |= sale_sudo.order_line.mapped("invoice_lines.move_id").filtered(
            lambda inv: inv.move_type == "out_invoice" and inv.state != "cancel"
        )
        invoices |= invoice_model.search(
            [
                ("move_type", "=", "out_invoice"),
                ("state", "!=", "cancel"),
                ("invoice_line_ids.sale_line_ids.order_id", "=", sale_sudo.id),
            ]
        )
        if sale_sudo.name:
            invoices |= invoice_model.search(
                [
                    ("move_type", "=", "out_invoice"),
                    ("state", "!=", "cancel"),
                    ("invoice_origin", "=", sale_sudo.name),
                ]
            )
            invoices |= invoice_model.search(
                [
                    ("move_type", "=", "out_invoice"),
                    ("state", "!=", "cancel"),
                    ("invoice_origin", "ilike", sale_sudo.name),
                ]
            )
        return invoices

    @api.constrains("requested_min_advance", "sale_order_total", "min_advance_required")
    def _check_requested_min_advance(self):
        for rec in self:
            if rec.requested_min_advance < 0:
                raise ValidationError("Requested minimum advance cannot be negative.")
            if rec.requested_min_advance > (rec.sale_order_total or 0.0):
                raise ValidationError("Requested minimum advance cannot exceed sale order total.")
            if rec.requested_min_advance >= (rec.min_advance_required or 0.0):
                raise ValidationError(
                    "Requested minimum advance must be lower than the standard 30% minimum."
                )

    def action_submit(self):
        for rec in self:
            if rec.state != "draft":
                continue
            if rec.requested_min_advance <= 0:
                raise UserError("Please enter requested minimum advance before submit.")
            rec.state = "submitted"

    def action_approve(self):
        for rec in self:
            if rec.state != "submitted":
                continue
            rec.write(
                {
                    "state": "approved",
                    "approved_by_id": self.env.user.id,
                    "approved_on": fields.Datetime.now(),
                    "rejection_reason": False,
                }
            )
            # ✅ Recompute supply eligibility on related pickings
            if rec.sale_order_id:
                appointments = self.env["resonnocare.appointment"].search(
                    [("sale_order_id", "=", rec.sale_order_id.id)]
                )
                for appt in appointments:
                    pickings = self.env["stock.picking"].search(
                        [
                            ("origin", "in", [appt.appointment_id, appt.name]),
                            ("is_clinic_supply", "=", True),
                            ("state", "not in", ("done", "cancel")),
                        ]
                    )
                    if pickings:
                        pickings._compute_is_supply_eligible()

    def action_reject(self):
        for rec in self:
            if rec.state != "submitted":
                continue
            rec.write(
                {
                    "state": "rejected",
                    "approved_by_id": False,
                    "approved_on": False,
                }
            )

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_reset_draft(self):
        self.write(
            {
                "state": "draft",
                "approved_by_id": False,
                "approved_on": False,
            }
        )
