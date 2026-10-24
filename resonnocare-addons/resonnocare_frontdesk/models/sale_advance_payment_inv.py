from odoo import api, fields, models
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    # 1. Only ONE definition of the field
    appointment_sale_type = fields.Selection(
        selection=[
            ('service', 'Service'),
            ('device', 'Device'),
        ],
        string="Appointment Sale Type",
        compute="_compute_appointment_sale_type",
    )

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

    # 2. Helper to get active orders
    @api.model
    def _get_active_sale_orders(self):
        if self.env.context.get("active_model") != "sale.order":
            return self.env["sale.order"]
        active_ids = self.env.context.get("active_ids") or []
        _logger.warning(f"🔥 Active sale order IDs: {active_ids}")
        return self.env["sale.order"].browse(active_ids).exists()

    # 3. Compute appointment_sale_type
    @api.depends_context("active_model", "active_ids")
    def _compute_appointment_sale_type(self):
        for rec in self:
            orders = rec._get_active_sale_orders()
            if orders:
                rec.appointment_sale_type = orders[0].appointment_sale_type
            else:
                rec.appointment_sale_type = False
            _logger.warning(f"🔥 Computed appointment_sale_type for wizard {rec.id}: {rec.appointment_sale_type}")

    # 4. Compute is_service_only_flow (depends on the previous field)
    @api.depends("appointment_sale_type")
    def _compute_is_service_only_flow(self):
        for rec in self:
            rec.is_service_only_flow = (rec.appointment_sale_type == 'service')
            _logger.warning(f"🔥 Computed is_service_only_flow for wizard {rec.id}: {rec.is_service_only_flow}")

    # 5. default_get (always runs when wizard opens)
    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        orders = self._get_active_sale_orders()
        if orders and orders[0].appointment_sale_type == 'service':
            vals["advance_payment_method"] = "delivered"
        return vals

    # 6. fields_get (controls dropdown selection)
    @api.model
    def fields_get(self, allfields=None, attributes=None):
        result = super().fields_get(allfields=allfields, attributes=attributes)
        orders = self._get_active_sale_orders()
        if "advance_payment_method" in result and orders and orders[0].appointment_sale_type == 'service':
            result["advance_payment_method"]["selection"] = [
                ("delivered", "Regular invoice (Full payment)")
            ]
        return result

    # 7. Validation on confirm
    def create_invoices(self):
        for wizard in self:
            orders = wizard._get_active_sale_orders()
            if orders and orders[0].appointment_sale_type == 'service':
                if wizard.advance_payment_method != "delivered":
                    raise UserError(
                        "Down payment options are not allowed for service appointments. "
                        "Please use Regular invoice (Full payment)."
                    )
        return super().create_invoices()