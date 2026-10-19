from odoo import models, fields, api
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    cash_deposit_state = fields.Selection([
        ('unreconciled', 'Unreconciled'),
        ('pending', 'Pending Verification'),
        ('reconciled', 'Reconciled'),
    ], default='unreconciled', copy=False, tracking=True,
       help="Reconciliation state for cash payments deposited to bank.")

    bank_deposit_id = fields.Many2one(
        'bank.deposit', string='Bank Deposit',
        ondelete='set null', copy=False, index=True,
    )

    is_cash_payment = fields.Boolean(
        compute='_compute_is_cash_payment', store=True,
    )
    is_red = fields.Boolean(compute='_compute_is_red', store=True)

    @api.depends('journal_id.type')
    def _compute_is_cash_payment(self):
        for rec in self:
            rec.is_cash_payment = rec.journal_id.type == 'cash'

    @api.depends('cash_deposit_state', 'is_cash_payment')
    def _compute_is_red(self):
        for rec in self:
            rec.is_red = rec.is_cash_payment and rec.cash_deposit_state == 'unreconciled'

    def action_open_deposit_wizard(self):
        """Triggered by the list-header 'Deposit to Bank' button.
        `self` = recordset of selected rows."""
        valid = self.filtered(
            lambda p: p.is_cash_payment
                      and p.cash_deposit_state == 'unreconciled'
                      and not p.bank_deposit_id
        )
        if not valid:
            raise UserError(
                "Select at least one unreconciled cash payment "
                "(not already attached to a deposit)."
            )
        return {
            'type': 'ir.actions.act_window',
            'name': 'Deposit to Bank',
            'res_model': 'deposit.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_payment_ids': [(6, 0, valid.ids)]},
        }