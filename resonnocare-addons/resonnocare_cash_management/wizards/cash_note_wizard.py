from odoo import models, fields, api

class CashNoteWizard(models.TransientModel):
    _name = 'cash.note.wizard'
    _description = 'Cash Note Wizard'

    payment_register_id = fields.Many2one('account.payment.register', string="Payment Register", ondelete='cascade')
    currency_id = fields.Many2one('res.currency', related='payment_register_id.currency_id')
    
    note_value = fields.Monetary(string="Bill Type", required=True, currency_field='currency_id')
    quantity = fields.Integer(string="Quantity", default=0, required=True)
    subtotal = fields.Monetary(string="Total", compute="_compute_subtotal", store=True, currency_field='currency_id')

    @api.depends('note_value', 'quantity')
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = rec.note_value * rec.quantity