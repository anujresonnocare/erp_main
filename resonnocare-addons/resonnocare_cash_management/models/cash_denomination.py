from odoo import models, fields, api

class PaymentCashDenomination(models.Model):
    _name = 'payment.cash.denomination'
    _description = 'Payment Cash Denomination'

    payment_id = fields.Many2one('account.payment', string="Payment", required=True, ondelete='cascade')
    currency_id = fields.Many2one('res.currency', related='payment_id.currency_id')
    note_value = fields.Monetary(string="Bill Type", required=True, currency_field='currency_id')
    quantity = fields.Integer(string="Quantity", default=1, required=True)
    subtotal = fields.Monetary(string="Total", compute="_compute_subtotal", store=True, currency_field='currency_id')

    @api.depends('note_value', 'quantity')
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = rec.note_value * rec.quantity