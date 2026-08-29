from odoo import api, fields, models

class PaymentMatchingWizard(models.TransientModel):
    _name = "payment.matching.wizard"
    _description = "Payment Matching"

    payment_id = fields.Many2one("account.payment", required=True)
    partner_id = fields.Many2one(related="payment_id.partner_id", readonly=True)
    amount = fields.Monetary(related="payment_id.amount", readonly=True)
    currency_id = fields.Many2one(related="payment_id.currency_id")
    invoice_line_ids = fields.Many2many("account.move")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        payment = self.env["account.payment"].browse(
            self.env.context.get("default_payment_id")
        )
        invoices = self.env["account.move"].search([
            ("partner_id","=",payment.partner_id.id),
            ("state","=","posted"),
            ("payment_state","in",["not_paid","partial"]),
            ("move_type","in",("out_invoice","out_refund","in_invoice","in_refund")),
        ])
        res["invoice_line_ids"] = [(6,0,invoices.ids)]
        return res

    def action_match(self):
        payment_line = self.payment_id.move_id.line_ids.filtered(
            lambda l: l.account_id.reconcile and not l.reconciled
        )
        for invoice in self.invoice_line_ids:
            invoice_lines = invoice.line_ids.filtered(
                lambda l: l.account_id == payment_line.account_id and not l.reconciled
            )
            (payment_line + invoice_lines).reconcile()
        return {"type":"ir.actions.act_window_close"}
