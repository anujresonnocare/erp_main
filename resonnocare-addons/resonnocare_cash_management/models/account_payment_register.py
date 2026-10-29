from odoo import models

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def action_create_payments(self):
        # Call super first (which handles standard Odoo creation or your Approval module)
        result = super(AccountPaymentRegister, self).action_create_payments()
        
        # After payment is created, find it and attach the cash notes
        payment = self.env['account.payment'].search(
            [('partner_id', '=', self.partner_id.id)], 
            order='id desc', 
            limit=1
        )
        
        if payment and self.journal_id.type == 'cash':
            if hasattr(self, 'cash_note_ids'):
                for note in self.cash_note_ids:
                    if note.quantity > 0:
                        self.env['payment.cash.denomination'].create({
                            'payment_id': payment.id,
                            'note_value': note.note_value,
                            'quantity': note.quantity,
                        })
            payment.action_validate()  # Validate the payment after attaching cash notes
        return result