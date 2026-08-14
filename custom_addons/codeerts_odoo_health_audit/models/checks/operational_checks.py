from odoo import api, models


class OperationalChecks(models.AbstractModel):
    _inherit = 'health.audit.engine'

    # --- Finance: draft customer invoices not yet posted -----------------
    # account.move.state (v19) = draft/posted/cancel ; move_type out_invoice.
    @api.model
    def _check_draft_customer_invoices(self, check):
        domain = [('move_type', '=', 'out_invoice'), ('state', '=', 'draft')]
        count = self.env['account.move'].search_count(domain)
        return count, str(domain), check.default_severity

    def _check_draft_customer_invoices_model(self):
        return 'account.move'

    # --- Sales: confirmed orders still waiting to be invoiced ------------
    # sale.order.state (v19) = draft/sent/sale/cancel ; invoice_status 'to invoice'.
    @api.model
    def _check_so_to_invoice(self, check):
        domain = [('state', '=', 'sale'), ('invoice_status', '=', 'to invoice')]
        count = self.env['sale.order'].search_count(domain)
        return count, str(domain), check.default_severity

    def _check_so_to_invoice_model(self):
        return 'sale.order'
