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
    invoice_ids = fields.Many2many('account.move', related='payment_id.reconciled_invoice_ids', string="Invoices")
    state = fields.Selection([
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string="Status", default='pending', required=True)

    def action_approve(self):
        for record in self:
            if record.state != 'pending':
                continue
            
            record.state = 'approved'
            
            payment = record.payment_id
            if payment.state == 'draft':
                # Posting the payment will automatically reconcile it with the invoice
                payment.action_post()

    def action_reject(self):
        for record in self:
            record.state = 'rejected'
            payment = record.payment_id
            if payment.state == 'draft':
                payment.action_cancel()