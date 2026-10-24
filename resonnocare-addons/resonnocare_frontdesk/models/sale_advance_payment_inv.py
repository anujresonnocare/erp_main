from odoo import api, fields, models
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    # 1. Regular fields (no compute)
    appointment_sale_type = fields.Selection(
        selection=[('service', 'Service'), ('device', 'Device')],
        string="Appointment Sale Type",
    )
    
    is_service_only_flow = fields.Boolean(
        string="Service-only flow",
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

    # 2. Force the values in default_get (this ALWAYS runs)
    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        
        orders = self._get_active_sale_orders()
        if orders:
            sale_type = orders[0].appointment_sale_type
            vals['appointment_sale_type'] = sale_type
            
            if sale_type == 'service':
                vals['is_service_only_flow'] = True
                vals["advance_payment_method"] = "delivered"
            else:
                vals['is_service_only_flow'] = False
                
        return vals

    # 3. Keep fields_get for dropdown filtering
    @api.model
    def fields_get(self, allfields=None, attributes=None):
        result = super().fields_get(allfields=allfields, attributes=attributes)
        orders = self._get_active_sale_orders()
        if "advance_payment_method" in result and orders and orders[0].appointment_sale_type == 'service':
            result["advance_payment_method"]["selection"] = [
                ("delivered", "Regular invoice (Full payment)")
            ]
        return result

    # 4. Validation
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