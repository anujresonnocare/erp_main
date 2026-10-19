from odoo import models, fields

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    cash_denomination_ids = fields.One2many(
        'payment.cash.denomination', 
        'payment_id', 
        string="Cash Notes"
    )


    is_cash_payment = fields.Boolean(
        string="Is Cash Payment", 
        compute="_compute_is_cash_payment"
    )

    @api.depends('journal_id', 'journal_id.type')
    def _compute_is_cash_payment(self):
        for payment in self:
            payment.is_cash_payment = payment.journal_id.type == 'cash'