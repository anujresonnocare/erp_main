from odoo import models, fields

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    cash_denomination_ids = fields.One2many(
        'payment.cash.denomination', 
        'payment_id', 
        string="Cash Notes"
    )