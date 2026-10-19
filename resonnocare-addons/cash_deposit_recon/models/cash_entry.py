from odoo import models, fields, api

class CashEntry(models.Model):
    _name = 'cash.entry'
    _description = 'Cash Entry'
    _order = 'date desc, id desc'

    name = fields.Char(string='Description', required=True)
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    amount = fields.Monetary(string='Amount', currency_field='currency_id', required=True)
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )
    payment_method = fields.Selection(
        [('cash', 'Cash')],
        default='cash',
        required=True,
    )
    partner_id = fields.Many2one('res.partner', string='Partner')

    state = fields.Selection([
        ('unreconciled', 'Unreconciled'),
        ('pending', 'Pending Verification'),
        ('reconciled', 'Reconciled'),
    ], default='unreconciled', required=True, tracking=True, copy=False)

    deposit_id = fields.Many2one(
        'bank.deposit',
        string='Bank Deposit',
        ondelete='set null',
        copy=False,
        index=True,
    )

    is_red = fields.Boolean(compute='_compute_is_red', store=True)

    @api.depends('state')
    def _compute_is_red(self):
        for rec in self:
            rec.is_red = (rec.state == 'unreconciled')

    def unlink(self):
        # Prevent deleting entries already attached to a deposit
        for rec in self:
            if rec.deposit_id and rec.deposit_id.state == 'submitted':
                from odoo.exceptions import UserError
                raise UserError(
                    "Cannot delete entry '%s': it is attached to a submitted deposit."
                    % rec.name
                )
        return super().unlink()

    def write(self, vals):
        # Lock amounts/state when attached to a submitted deposit
        if 'amount' in vals or 'state' in vals:
            for rec in self:
                if rec.deposit_id and rec.deposit_id.state == 'submitted':
                    # Allow internal state change only from the deposit workflow
                    if self.env.context.get('from_deposit_workflow'):
                        continue
                    if 'state' in vals and vals['state'] in ('pending', 'reconciled'):
                        continue  # workflow-driven
                    from odoo.exceptions import UserError
                    raise UserError(
                        "Entry '%s' is locked inside a submitted deposit." % rec.name
                    )
        return super().write(vals)