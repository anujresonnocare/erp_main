from odoo import models

class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_payment_matching(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Payment Matching",
            "res_model": "payment.matching.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_payment_id": self.id},
        }
