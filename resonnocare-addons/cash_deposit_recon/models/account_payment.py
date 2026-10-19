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


    def open_payment_matching_screen(self):
        self.ensure_one()

        if not self.partner_id:
            raise UserError(_("Payments without a customer or vendor can't be matched."))

        # 1. Fetch the un-reconciled line that belongs to a receivable/payable account
        move_line = self.move_id.line_ids.filtered(
            lambda l: l.account_id.reconcile and not l.reconciled
        )[:1]

        # 2. Build the standard modern window action pointing to the account.move.line model
        action = {
            'name': _('Payment Matching'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list',
            'target': 'current',
            'domain': [
                ('partner_id', '=', self.partner_id.commercial_partner_id.id),
                ('account_id.reconcile', '=', True),
                ('reconciled', '=', False),
            ],
            'context': {
                'company_ids': [self.company_id.id],
                'search_default_partner_id': self.partner_id.commercial_partner_id.id,
            }
        }

        # 3. Focus the view onto the exact payment move line if one exists
        if move_line:
            action['context']['search_default_id'] = move_line.id

        return action