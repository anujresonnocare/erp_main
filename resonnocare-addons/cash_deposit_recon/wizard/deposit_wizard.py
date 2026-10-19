from odoo import models, fields, api
from odoo.exceptions import UserError


class DepositWizard(models.TransientModel):
    _name = 'deposit.wizard'
    _description = 'Create Bank Deposit'

    bank_account_id = fields.Many2one(
        'account.account', string='Bank Account', required=True,
        domain="[('account_type', '=', 'asset_cash')]",
    )
    deposit_date = fields.Date(default=fields.Date.context_today, required=True)
    reference = fields.Char(string='Deposit Reference')

    slip_attachment = fields.Binary(
        string='Deposit Slip', required=True, attachment=True,
    )
    slip_filename = fields.Char()

    payment_ids = fields.Many2many(
        'account.payment', string='Selected Payments', readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id,
    )
    total_amount = fields.Monetary(
        compute='_compute_total', currency_field='currency_id',
    )

    @api.depends('payment_ids')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.payment_ids.mapped('amount'))

    def action_create_deposit(self):
        self.ensure_one()
        if not self.payment_ids:
            raise UserError("No valid cash payments selected.")
        if not self.slip_attachment:
            raise UserError("Deposit slip attachment is required.")

        deposit = self.env['bank.deposit'].create({
            'bank_account_id': self.bank_account_id.id,
            'deposit_date': self.deposit_date,
            'reference': self.reference,
            'slip_attachment': self.slip_attachment,
            'slip_filename': self.slip_filename,
        })

        self.payment_ids.write({
            'bank_deposit_id': deposit.id,
            'cash_deposit_state': 'pending',
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Bank Deposit',
            'res_model': 'bank.deposit',
            'res_id': deposit.id,
            'view_mode': 'form',
            'target': 'current',
        }