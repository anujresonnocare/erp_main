from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    is_cash_journal = fields.Boolean(compute="_compute_is_cash_journal")
    cash_note_ids = fields.One2many('cash.note.wizard', 'payment_register_id', string="Cash Breakdown")
    cash_total_entered = fields.Monetary(string="Cash Total", compute="_compute_cash_total")
    
    @api.depends('journal_id')
    def _compute_is_cash_journal(self):
        for wizard in self:
            wizard.is_cash_journal = wizard.journal_id.type == 'cash'

    @api.depends('cash_note_ids.subtotal')
    def _compute_cash_total(self):
        for wizard in self:
            wizard.cash_total_entered = sum(wizard.cash_note_ids.mapped('subtotal'))

    @api.onchange('journal_id')
    def _onchange_journal_id_cash_defaults(self):
        self.cash_note_ids = [(5, 0, 0)]
        if self.journal_id and self.journal_id.type == 'cash':
            # Default fixed denomination list
            default_notes = [500.0, 200.0, 100.0, 50.0, 20.0, 10.0, 5.0, 2.0, 1.0]
            lines = []
            for note in default_notes:
                lines.append((0, 0, {'note_value': note, 'quantity': 0}))
            self.cash_note_ids = lines

    def action_create_payments(self):
        # 1. VALIDATION FOR CASH
        if self.journal_id.type == 'cash':
            total_entered = sum(self.cash_note_ids.mapped('subtotal'))
            if total_entered == 0:
                raise UserError(_("You must enter the Cash Breakdown (Notes/Coins) to proceed."))
            if round(total_entered, 2) != round(self.amount, 2):
                raise UserError(_("The total cash entered (%s) does not match the payment amount (%s). Please check the denominations.") % (total_entered, self.amount))

        # 2. CALL SUPER
        return super(AccountPaymentRegister, self).action_create_payments()