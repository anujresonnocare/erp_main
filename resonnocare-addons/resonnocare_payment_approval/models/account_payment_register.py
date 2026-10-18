from odoo import models, _
from odoo.exceptions import UserError

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def action_create_payments(self):
        # Check if the selected journal requires approval
        if self.journal_id.requires_payment_approval:
            # 1. Create the payment but DO NOT post it (keeps it in draft)
            payments = self._create_payments()
            
            for payment in payments:
                # 2. Create the approval record
                self.env['payment.approval'].create({
                    'payment_id': payment.id,
                    'name': payment.name,
                })
            
            # 3. Return an action that closes the wizard and shows a notification
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Approval Required'),
                    'message': _('Payment created in Draft. Waiting for Finance Approval.'),
                    'type': 'warning',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        
        # If no approval needed, proceed with standard behavior
        return super(AccountPaymentRegister, self).action_create_payments()