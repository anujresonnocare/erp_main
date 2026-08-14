from odoo import models
from odoo.exceptions import UserError


class StockQuant(models.Model):
    _inherit = "stock.quant"

    def action_open_clinic_stock(self):
        user = self.env.user
        clinic = user.clinic_id or user.employee_id.clinic_id
        if not clinic or not clinic.stock_location_id:
            raise UserError("Clinic stock location is not configured for this user.")

        return {
            "type": "ir.actions.act_window",
            "name": "Clinic Stock",
            "res_model": "stock.quant",
            "view_mode": "list,form",
            "domain": [("location_id", "child_of", clinic.stock_location_id.id)],
            "context": {
                "search_default_location_id": clinic.stock_location_id.id,
            },
        }
