from odoo import api, fields, models
from odoo.exceptions import UserError

class PaymentMatchingWizard(models.TransientModel):
    _name="payment.matching.wizard"
    _description="Payment Matching Wizard"

    payment_id=fields.Many2one("account.payment",required=True,readonly=True)
    partner_id=fields.Many2one(related="payment_id.partner_id",readonly=True)
    currency_id=fields.Many2one(related="payment_id.currency_id",readonly=True)
    payment_amount=fields.Monetary(related="payment_id.amount",readonly=True)
    remaining_amount=fields.Monetary(compute="_compute_remaining")
    total_selected=fields.Monetary(compute="_compute_remaining")
    invoice_ids=fields.Many2many("account.move",string="Invoices")

    @api.depends("invoice_ids")
    def _compute_remaining(self):
        for wizard in self:
            total=sum(wizard.invoice_ids.mapped("amount_residual"))
            wizard.total_selected=total
            wizard.remaining_amount=wizard.payment_amount-total

    @api.model
    def default_get(self, fields_list):
        res=super().default_get(fields_list)
        payment=self.env["account.payment"].browse(self.env.context.get("default_payment_id"))
        invoices=self.env["account.move"].search([
            ("partner_id","=",payment.partner_id.id),
            ("state","=","posted"),
            ("payment_state","in",["not_paid","partial"]),
            ("move_type","in",("out_invoice","out_refund","in_invoice","in_refund")),
        ])
        res.update({"invoice_ids":[(6,0,invoices.ids)]})
        return res

    def action_match(self):
        self.ensure_one()
        if not self.invoice_ids:
            raise UserError("Please select invoice.")
        payment_lines=self.payment_id.move_id.line_ids.filtered(lambda l:l.account_id.reconcile and not l.reconciled)
        if not payment_lines:
            raise UserError("Nothing left to reconcile.")
        for invoice in self.invoice_ids:
            invoice_lines=invoice.line_ids.filtered(lambda l:l.account_id==payment_lines.account_id and not l.reconciled)
            (payment_lines+invoice_lines).reconcile()
        return {"type":"ir.actions.act_window_close"}
