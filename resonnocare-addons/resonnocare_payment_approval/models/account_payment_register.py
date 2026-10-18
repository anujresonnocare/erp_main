from odoo import models, _
from odoo.exceptions import UserError

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def action_create_payments(self):
        # Check if the selected journal requires approval
        if self.journal_id.requires_payment_approval:
            
            # 1. Create the payment in Draft (without auto-reconciling)
            # We temporarily remove the context that forces immediate payment
            wizard_context = self.env.context.copy()
            self.env.context = dict(wizard_context, dont_redirect_to_payments=True)
            
            # Create the payment
            payments = self._create_payments()
            
            for payment in payments:
                # # 2. Create the approval record
                # self.env['payment.approval'].create({
                #     'payment_id': payment.id,
                #     'name': payment.name,
                # })

                # 2. Create the approval record
                self.env['payment.approval'].create({
                    'payment_id': payment.id,
                    'name': payment.name,
                    'invoice_ids': [(6, 0, self.env.context.get('active_ids', []))] # <-- ADD THIS
                })
                
                # 3. IMPORTANT: In Odoo 18, _create_payments auto-reconciles the invoice.
                # We must break that link so the invoice stays Unpaid!
                payment_lines = payment.move_id.line_ids.filtered(
                    lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
                )
                for line in payment_lines:
                    line.remove_move_reconcile()
            
            # 4. Show notification and close wizard
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Approval Required'),
                    'message': _('Payment created. Waiting for Finance Approval.'),
                    'type': 'warning',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        
        # If no approval needed, proceed with standard behavior
        return super(AccountPaymentRegister, self).action_create_payments()