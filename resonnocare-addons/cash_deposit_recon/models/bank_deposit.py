from odoo import models, fields, api
from odoo.exceptions import UserError


class BankDeposit(models.Model):
    _name = 'bank.deposit'
    _description = 'Bank Deposit'
    _order = 'deposit_date desc, id desc'

    name = fields.Char(default='New', readonly=True, copy=False)
    deposit_date = fields.Date(
        string='Deposit Date', default=fields.Date.context_today, required=True,
    )
    bank_account_id = fields.Many2one(
        'account.account', string='Bank Account', required=True,
        domain="[('account_type', '=', 'asset_cash')]",
    )
    reference = fields.Char(string='Deposit Reference')

    payment_ids = fields.One2many(
        'account.payment', 'bank_deposit_id', string='Cash Payments',
    )

    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id,
    )
    total_amount = fields.Monetary(
        compute='_compute_total', store=True, currency_field='currency_id',
    )
    entry_count = fields.Integer(compute='_compute_total')

    slip_attachment = fields.Binary(
        string='Deposit Slip', attachment=True, required=True,
    )
    slip_filename = fields.Char()

    state = fields.Selection([
        ('submitted', 'Pending Verification'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ], default='submitted', required=True, tracking=True, copy=False)

    submitted_by = fields.Many2one(
        'res.users', default=lambda self: self.env.user, readonly=True,
    )
    submitted_date = fields.Datetime(default=fields.Datetime.now, readonly=True)
    verified_by = fields.Many2one('res.users', readonly=True, copy=False)
    verified_date = fields.Datetime(readonly=True, copy=False)
    reject_reason = fields.Text(copy=False)

    @api.depends('payment_ids.amount')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.payment_ids.mapped('amount'))
            rec.entry_count = len(rec.payment_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('bank.deposit') or 'New'
        return super().create(vals_list)

    def action_verify(self):
        for rec in self:
            if rec.state != 'submitted':
                raise UserError("Only submitted deposits can be verified.")
            rec.write({
                'state': 'verified',
                'verified_by': self.env.user.id,
                'verified_date': fields.Datetime.now(),
            })
            rec.payment_ids.write({'cash_deposit_state': 'reconciled'})

    def action_reject(self):
        for rec in self:
            if rec.state != 'submitted':
                raise UserError("Only submitted deposits can be rejected.")
            if not rec.reject_reason:
                raise UserError("Please fill in the reject reason before rejecting.")
            rec.payment_ids.write({
                'cash_deposit_state': 'unreconciled',
                'bank_deposit_id': False,
            })
            rec.write({'state': 'rejected'})