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

    slip_attachment = fields.Binary(string='Deposit Slip', required=True, attachment=True)
    slip_filename = fields.Char()

    cash_entry_ids = fields.Many2many('cash.entry', string='Selected Entries', readonly=True)
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )
    total_amount = fields.Monetary(
        compute='_compute_total', currency_field='currency_id',
    )

    @api.depends('cash_entry_ids')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.cash_entry_ids.mapped('amount'))

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            entries = self.env['cash.entry'].browse(active_ids)
            # Only unreconciled entries with no deposit
            valid = entries.filtered(
                lambda e: e.state == 'unreconciled' and not e.deposit_id
            )
            res['cash_entry_ids'] = [(6, 0, valid.ids)]
        return res

    def action_create_deposit(self):
        self.ensure_one()
        if not self.cash_entry_ids:
            raise UserError("No valid cash entries selected.")
        if not self.slip_attachment:
            raise UserError("Deposit slip attachment is required.")

        deposit = self.env['bank.deposit'].create({
            'bank_account_id': self.bank_account_id.id,
            'deposit_date': self.deposit_date,
            'reference': self.reference,
            'slip_attachment': self.slip_attachment,
            'slip_filename': self.slip_filename,
        })

        self.cash_entry_ids.with_context(from_deposit_workflow=True).write({
            'deposit_id': deposit.id,
            'state': 'pending',
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Bank Deposit',
            'res_model': 'bank.deposit',
            'res_id': deposit.id,
            'view_mode': 'form',
            'target': 'current',
        }