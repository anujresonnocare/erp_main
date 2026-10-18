from odoo import models, fields, api, _

class PaymentApproval(models.Model):
    _name = 'payment.approval'
    _description = 'Payment Approval'
    _order = 'create_date desc'

    name = fields.Char(string="Reference", readonly=True, default="New")
    payment_id = fields.Many2one('account.payment', string="Payment", required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', related='payment_id.partner_id', string="Customer/Vendor", store=True)
    amount = fields.Monetary(related='payment_id.amount', string="Amount", store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='payment_id.currency_id')
    journal_id = fields.Many2one('account.journal', related='payment_id.journal_id', string="Journal")
    
    # We need to link the invoices manually since they aren't reconciled yet
    invoice_ids = fields.Many2many('account.move', string="Invoices") 
    
    state = fields.Selection([
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string="Status", default='pending', required=True)

    def action_approve(self):
        for record in self:
            if record.state != 'pending':
                continue
            
            payment = record.payment_id
            invoices = record.invoice_ids
            
            # 1. Post the payment
            if payment.state == 'draft':
                payment.action_post()
            
            # 2. Reconcile the payment with the invoice now that it's approved
            if invoices:
                payment_lines = payment.move_id.line_ids.filtered(
                    lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
                )
                invoice_lines = invoices.mapped('line_ids').filtered(
                    lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable') and not l.reconciled
                )
                
                if payment_lines and invoice_lines:
                    (payment_lines + invoice_lines).reconcile()

            record.state = 'approved'

    def action_reject(self):
        for record in self:
            record.state = 'rejected'
            payment = record.payment_id
            if payment.state == 'draft':
                payment.action_cancel()