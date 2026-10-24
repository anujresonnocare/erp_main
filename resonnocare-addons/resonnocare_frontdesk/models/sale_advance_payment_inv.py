from odoo import api, fields, models
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


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
        _logger.debug(f"Active sale order IDs: {active_ids}")
        return self.env["sale.order"].browse(active_ids).exists()

    @api.model
    def _is_service_appointment(self):
        """Check if any active sale order has appointment_sale_type == 'service'"""
        orders = self._get_active_sale_orders()
        if not orders:
            return False
        _logger.debug(f"Checking service appointment for orders: {orders.ids}")
        aat = any(order.appointment_sale_type == 'service' for order in orders)
        _logger.debug(f"Is service appointment: 44444444444444444444{aat}")
        self.is_service_only_flow = aat
        # Check strictly on the appointment_sale_type field of the sale.order
        return any(order.appointment_sale_type == 'service' for order in orders)

    @api.depends_context("active_model", "active_ids")
    def _compute_is_service_only_flow(self):
        flag = self._is_service_appointment()
        for rec in self:
            _logger.debug(f"Setting is_service_only_flow for record 11111111111{rec.id} to {flag}")
            rec.is_service_only_flow = flag
            _logger.debug(f"Record {rec.id} is_service_only_flow set to 2222222222222{rec.is_service_only_flow}")


    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        if self._is_service_appointment():
            vals["advance_payment_method"] = "delivered"
        return vals

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        result = super().fields_get(allfields=allfields, attributes=attributes)
        if "advance_payment_method" in result and self._is_service_appointment():
            result["advance_payment_method"]["selection"] = [
                ("delivered", "Regular invoice (Full payment)")
            ]
        return result

    def create_invoices(self):
        for wizard in self:
            if wizard._is_service_appointment() and wizard.advance_payment_method != "delivered":
                raise UserError(
                    "Down payment options are not allowed for service appointments. "
                    "Please use Regular invoice (Full payment)."
                )
        return super().create_invoices()