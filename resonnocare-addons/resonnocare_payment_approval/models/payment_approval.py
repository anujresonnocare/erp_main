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
            
            payment = record.payment_id
            
            # 1. Post the payment if it's still draft
            if payment.state == 'draft' or payment.state == 'in_process':
                payment.action_post()
            
            # 2. Find the invoices related to this payment.
            # We look at the payment's context or the linked move lines.
            # Since the payment wizard creates the payment and links it, we can use Odoo's built-in reconciliation helper.
            
            # Fetch the receivable/payable lines of the payment
            payment_lines = payment.move_id.line_ids.filtered(
                lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable')
            )
            
            # If invoices are already linked, use them. Otherwise, we try to find them from the context.
            invoices = record.invoice_ids
            if not invoices:
                # Fallback: find invoices waiting for this payment amount & partner
                # (This is a safety net, though the related field should work)
                pass

            if invoices and payment_lines:
                invoice_lines = invoices.mapped('line_ids').filtered(
                    lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable') 
                    and not line.reconciled
                )
                
                if invoice_lines:
                    (payment_lines + invoice_lines).reconcile()
            
            record.state = 'approved'

    def action_reject(self):
        for record in self:
            record.state = 'rejected'
            payment = record.payment_id
            if payment.state == 'draft':
                payment.action_cancel()