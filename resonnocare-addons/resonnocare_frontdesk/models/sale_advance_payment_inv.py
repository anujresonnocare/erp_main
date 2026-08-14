from odoo import api, fields, models
from odoo.exceptions import UserError


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    is_service_only_flow = fields.Boolean(
        string="Service-only flow",
        compute="_compute_is_service_only_flow",
    )

    advance_payment_method = fields.Selection(
        selection=[
            ("delivered", "Regular invoice (Full payment)"),
            ("percentage", "Down payment (percentage)"),
            ("fixed", "Down payment (fixed amount)"),
        ],
        string="Create Invoice",
        default="delivered",
        required=True,
    )

    @api.model
    def _get_active_sale_orders(self):
        if self.env.context.get("active_model") != "sale.order":
            return self.env["sale.order"]
        active_ids = self.env.context.get("active_ids") or []
        return self.env["sale.order"].browse(active_ids).exists()

    @api.model
    def _is_service_only_sale_flow(self):
        orders = self._get_active_sale_orders()
        if not orders:
            return False
        lines = orders.mapped("order_line").filtered(
            lambda l: not l.display_type and not getattr(l, "is_downpayment", False)
        )
        if not lines:
            return False
        return all((l.product_id and l.product_id.type == "service") for l in lines)

    @api.depends_context("active_model", "active_ids")
    def _compute_is_service_only_flow(self):
        flag = self._is_service_only_sale_flow()
        for rec in self:
            rec.is_service_only_flow = flag

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        if self._is_service_only_sale_flow():
            vals["advance_payment_method"] = "delivered"
        return vals

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        result = super().fields_get(allfields=allfields, attributes=attributes)
        if "advance_payment_method" in result and self._is_service_only_sale_flow():
            result["advance_payment_method"]["selection"] = [
                ("delivered", "Regular invoice (Full payment)")
            ]
        return result

    def create_invoices(self):
        for wizard in self:
            if wizard._is_service_only_sale_flow() and wizard.advance_payment_method != "delivered":
                raise UserError(
                    "Down payment options are not allowed for service-only sales. "
                    "Please use Regular invoice (Full payment)."
                )
        return super().create_invoices()
