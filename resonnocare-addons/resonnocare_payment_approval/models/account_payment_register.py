from odoo import models, _
from odoo.exceptions import UserError

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def action_create_payments(self):
        # Check if the selected journal requires approval
        if self.journal_id.requires_payment_approval:
            
            # 1. We trick Odoo into not posting/reconciling automatically.
            # We use a safe context copy and inject a flag that prevents standard reconciliation.
            # (In Odoo 18, standard reconciliation happens inside _create_payments)
            wizard_context = self.env.context.copy()
            self.env.context = dict(wizard_context, skip_auto_reconcile=True)
            
            # 2. Create the payment
            payments = self._create_payments()
            
            for payment in payments:
                # 3. Create the approval record safely
                self.env['payment.approval'].create({
                    'payment_id': payment.id,
                    'name': payment.name,
                })
                
                # 4. Just to be absolutely safe: If Odoo somehow still reconciled it,
                # we manually remove the reconciliation link so the invoice stays "Unpaid".
                payment_lines = payment.move_id.line_ids.filtered(
                    lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
                )
                for line in payment_lines:
                    line.remove_move_reconcile()
            
            # 5. Return an action that closes the wizard and shows a notification
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