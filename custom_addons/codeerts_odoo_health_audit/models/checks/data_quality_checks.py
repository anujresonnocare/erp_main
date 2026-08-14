from odoo import api, models


class DataQualityChecks(models.AbstractModel):
    _inherit = 'health.audit.engine'

    # --- res.partner: contacts with no email -----------------------------
    @api.model
    def _check_partner_no_email(self, check):
        # res.partner.type selection (v19) = contact/invoice/delivery/other.
        # Restrict to real contact records (not child invoice/delivery addresses).
        domain = [('type', '=', 'contact'), ('email', '=', False)]
        count = self.env['res.partner'].search_count(domain)
        return count, str(domain), check.default_severity

    def _check_partner_no_email_model(self):
        return 'res.partner'

    # --- res.partner: contacts with no country ---------------------------
    @api.model
    def _check_partner_no_country(self, check):
        domain = [('type', '=', 'contact'), ('country_id', '=', False)]
        count = self.env['res.partner'].search_count(domain)
        return count, str(domain), check.default_severity

    def _check_partner_no_country_model(self):
        return 'res.partner'

    # --- product.template: no cost (standard_price = 0) ------------------
    @api.model
    def _check_product_no_cost(self, check):
        domain = [('standard_price', '=', 0.0)]
        count = self.env['product.template'].search_count(domain)
        return count, str(domain), check.default_severity

    def _check_product_no_cost_model(self):
        return 'product.template'

    # --- product.template: no sale price (list_price = 0) ----------------
    @api.model
    def _check_product_no_sale_price(self, check):
        domain = [('list_price', '=', 0.0)]
        count = self.env['product.template'].search_count(domain)
        return count, str(domain), check.default_severity

    def _check_product_no_sale_price_model(self):
        return 'product.template'

    # --- res.partner: contacts with no phone -----------------------------
    @api.model
    def _check_partner_no_phone(self, check):
        domain = [('type', '=', 'contact'), ('phone', '=', False)]
        count = self.env['res.partner'].search_count(domain)
        return count, str(domain), check.default_severity

    def _check_partner_no_phone_model(self):
        return 'res.partner'
