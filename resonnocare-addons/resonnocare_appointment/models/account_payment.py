from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class AccountPayment(models.Model):
    _inherit = "account.payment"

    upi_transaction_id = fields.Char("UPI Transaction ID")
    cheque_number = fields.Char("Cheque Number")
    cheque_date = fields.Date("Cheque Date")
    cheque_bank_name = fields.Char("Cheque Bank")
    paytm_txn_id = fields.Char("Paytm Transaction ID")

    sub_mode = fields.Many2one("sub.mode")

    is_upi_journal = fields.Boolean()
    is_cheque_journal = fields.Boolean()
    is_paytm_journal = fields.Boolean()



    payment_mode      = fields.Selection([
        ("cash", "Cash"),
        ("POS", "POS"), ("Online", "Online"), ("Cheque", "Cheque"), ("EMI", "EMI"),
    ], string="Payment Mode")
    sub_mode_pos      = fields.Selection([
        ("UPI", "UPI"), ("Credit_Card", "Credit Card"),
        ("Debit_Card", "Debit Card"), ("Pay_by_Link", "Pay by Link"),
    ], string="Sub Mode (POS)")
    sub_mode_online   = fields.Selection([
        ("NEFT", "NEFT"), ("IMPS", "IMPS"), ("RTGS", "RTGS"),
    ], string="Sub Mode (Online)")
    sub_mode_emi      = fields.Selection([
        ("No_Cost_EMI", "No Cost EMI"), ("Regular_EMI", "Regular EMI"),
    ], string="Sub Mode (EMI)")
    pay_type_upi      = fields.Selection([("DQR", "DQR"), ("SQR", "SQR")], string="UPI Type")
    pay_type_card     = fields.Selection([
        ("Mastercard", "Mastercard"), ("VISA", "VISA"), ("Rupay", "Rupay"),
        ("Maestro", "Maestro"), ("Diners", "Diners"), ("Amex", "Amex"),
    ], string="Card Type")
    pay_type_link     = fields.Selection([("Card", "Card")], string="Pay by Link Type")
    reference_no      = fields.Char("Reference No")
    payment_date      = fields.Date("Payment Date")
    cheque_no         = fields.Char("Cheque No")
    cheque_date       = fields.Date("Cheque Date")
    # cheque_bank_name  = fields.Selection(selection=[], string='Bank Name')  # reuse same list
    cheque_bank_name = fields.Selection([
            ('sbi', 'State Bank of India (SBI)'),
            ('bob', 'Bank of Baroda (BOB)'),
            ('boi', 'Bank of India (BOI)'),
            ('bom', 'Bank of Maharashtra (BOM)'),
            ('canara', 'Canara Bank'),
            ('central', 'Central Bank of India'),
            ('indian_bank', 'Indian Bank'),
            ('iob', 'Indian Overseas Bank (IOB)'),
            ('pnb', 'Punjab National Bank (PNB)'),
            ('punjab_sind', 'Punjab & Sind Bank'),
            ('uco', 'UCO Bank'),
            ('union', 'Union Bank of India'),
            ('hdfc', 'HDFC Bank'),
            ('icici', 'ICICI Bank'),
            ('axis', 'Axis Bank'),
            ('kotak', 'Kotak Mahindra Bank'),
            ('indusind', 'IndusInd Bank'),
            ('idbi', 'IDBI Bank'),
            ('idfc_first', 'IDFC FIRST Bank'),
            ('federal', 'Federal Bank'),
            ('yes_bank', 'Yes Bank'),
            ('rbl', 'RBL Bank'),
            ('south_indian', 'South Indian Bank'),
            ('karnataka', 'Karnataka Bank'),
            ('karur_vysya', 'Karur Vysya Bank'),
            ('city_union', 'City Union Bank'),
            ('dhanlaxmi', 'Dhanlaxmi Bank'),
            ('tamilnad_mercantile', 'Tamilnad Mercantile Bank'),
            ('csb', 'CSB Bank'),
            ('jk_bank', 'Jammu & Kashmir Bank'),
            ('bandhan', 'Bandhan Bank'),
            ('dcb', 'DCB Bank'),
            ('nainital', 'Nainital Bank'),
            ('au_sfb', 'AU Small Finance Bank'),
            ('equitas_sfb', 'Equitas Small Finance Bank'),
            ('ujjivan_sfb', 'Ujjivan Small Finance Bank'),
            ('jana_sfb', 'Jana Small Finance Bank'),
            ('suryoday_sfb', 'Suryoday Small Finance Bank'),
            ('utkarsh_sfb', 'Utkarsh Small Finance Bank'),
            ('esaf_sfb', 'ESAF Small Finance Bank'),
            ('fincare_sfb', 'Fincare Small Finance Bank'),
            ('shivalik_sfb', 'Shivalik Small Finance Bank'),
            ('ne_sfb', 'North East Small Finance Bank'),
            ('airtel_pb', 'Airtel Payments Bank'),
            ('ippb', 'India Post Payments Bank'),
            ('fino_pb', 'Fino Payments Bank'),
            ('paytm_pb', 'Paytm Payments Bank'),
            ('nsdl_pb', 'NSDL Payments Bank'),
            ('aryavart_rgb', 'Aryavart Bank'),
            ('baroda_rajasthan_rgb', 'Baroda Rajasthan Kshetriya Gramin Bank'),
            ('kerala_gb', 'Kerala Gramin Bank'),
            ('karnataka_gb', 'Karnataka Gramin Bank'),
            ('maharashtra_gb', 'Maharashtra Gramin Bank'),
            ('rajasthan_marudhara_gb', 'Rajasthan Marudhara Gramin Bank'),
            ('punjab_gb', 'Punjab Gramin Bank'),
            ('assam_gvb', 'Assam Gramin Vikash Bank'),
            ('bihar_gb', 'Bihar Gramin Bank'),
            ('jharkhand_rgb', 'Jharkhand Rajya Gramin Bank'),
            ('up_gb', 'Uttar Pradesh Gramin Bank'),
            ('ap_gvb', 'Andhra Pradesh Grameena Vikas Bank'),
            ('telangana_gb', 'Telangana Grameena Bank'),
            ('tamilnadu_gb', 'Tamil Nadu Grama Bank'),
            ('odisha_gb', 'Odisha Gramya Bank'),
            ('chhattisgarh_rgb', 'Chhattisgarh Rajya Gramin Bank'),
            ('mp_gb', 'Madhya Pradesh Gramin Bank'),
            ('uttarakhand_gb', 'Uttarakhand Gramin Bank'),
            ('tripura_gb', 'Tripura Gramin Bank'),
            ('meghalaya_rb', 'Meghalaya Rural Bank'),
            ('hsbc', 'HSBC'),
            ('standard_chartered', 'Standard Chartered Bank'),
            ('citibank', 'Citibank'),
            ('dbs', 'DBS Bank'),
            ('deutsche', 'Deutsche Bank'),
            ('boa', 'Bank of America'),
            ('barclays', 'Barclays Bank'),
            ('bnp_paribas', 'BNP Paribas'),
            ('bank_of_china', 'Bank of China'),
            ('jp_morgan', 'J.P. Morgan Chase Bank'),
            ('mufg', 'MUFG Bank'),
            ('societe_generale', 'Société Générale'),
            ('credit_agricole', 'Crédit Agricole'),
            ('qnb', 'Qatar National Bank'),
            ('mizuho', 'Mizuho Bank'),
            ('smbc', 'Sumitomo Mitsui Banking Corporation (SMBC)'),
            ('scotiabank', 'Bank of Nova Scotia'),
            ('anz', 'Australia and New Zealand Banking Group (ANZ)'),
            ('saraswat_coop', 'Saraswat Cooperative Bank'),
            ('cosmos_coop', 'Cosmos Cooperative Bank'),
            ('abhyudaya_coop', 'Abhyudaya Cooperative Bank'),
            ('bharat_coop', 'Bharat Cooperative Bank'),
            ('shamrao_vithal_coop', 'Shamrao Vithal Cooperative Bank'),
            ('tjsb_coop', 'TJSB Sahakari Bank'),
            ('kalupur_coop', 'Kalupur Commercial Cooperative Bank'),
            ('ahmedabad_mercantile_coop', 'Ahmedabad Mercantile Cooperative Bank'),
            ('janata_sahakari', 'Janata Sahakari Bank'),
            ('rajkot_nagrik_coop', 'Rajkot Nagrik Sahakari Bank'),
        ], string='Bank Name')
    partner_name      = fields.Selection([
        ("Paytm", "Paytm"), ("HDFC", "HDFC"), ("Shopse", "Shopse"), ("FIBER", "FIBER"),
    ], string="Partner Name")
    scheme_name       = fields.Char("Scheme Name")


    def _is_resonnocare_customer_receipt(self):
        self.ensure_one()
        return self.partner_type == "customer" and self.payment_type == "inbound"

    def _get_receipt_clinic(self):
        self.ensure_one()
        invoices = self.reconciled_invoice_ids
        clinic = invoices[:1].clinic_id if invoices else False
        if not clinic and self.partner_id and getattr(self.partner_id, "clinic_id", False):
            clinic = self.partner_id.clinic_id
        return clinic

    def _get_receipt_paid_for_label(self):
        self.ensure_one()
        invoices = self.reconciled_invoice_ids
        categories = set(invoices.mapped("custom_invoice_category"))
        currency = self.currency_id or self.company_id.currency_id
        is_final_payment = False

        # Prefer sale-order-level paid-vs-total check (robust, same approach as appointment balance flow).
        sale_orders = self._get_receipt_related_sale_orders(invoices)

        if sale_orders:
            is_final_payment = True
            for sale in sale_orders:
                related_invoices = self._get_receipt_related_customer_invoices(sale)
                posted_customer_invoices = related_invoices.filtered(lambda inv: inv.state == "posted")
                total_payable = sale.amount_total or 0.0
                paid_total = sum(
                    inv._get_contract_advance_paid() if hasattr(inv, "_get_contract_advance_paid")
                    else ((inv.amount_total or 0.0) - (inv.amount_residual or 0.0))
                    for inv in posted_customer_invoices
                )
                sale_currency = sale.currency_id or currency
                due = total_payable - paid_total
                if not (sale_currency and sale_currency.is_zero(due)):
                    is_final_payment = False
                    break
        else:
            is_final_payment = bool(
                invoices
                and all(
                    not inv.amount_residual
                    or (currency and currency.is_zero(inv.amount_residual))
                    for inv in invoices
                )
            )
        if "HI" in categories or "HC" in categories:
            return "HI. & Accessories" if is_final_payment else "Advance of HI. & Accessories"
        if "DI" in categories or "DC" in categories:
            return "Diagnostic Services"
        if "RI" in categories or "RC" in categories:
            return "Repair Services"
        return "Payment"

    def _get_receipt_related_sale_orders(self, invoices):
        self.ensure_one()
        sale_orders = invoices.mapped("invoice_line_ids.sale_line_ids.order_id")
        if sale_orders:
            return sale_orders

        so_names = set()
        for inv in invoices:
            if inv.invoice_origin:
                so_names.update(
                    [name.strip() for name in inv.invoice_origin.split(",") if name.strip()]
                )
        if so_names:
            sale_orders |= self.env["sale.order"].search([("name", "in", list(so_names))])
        return sale_orders

    def _get_receipt_related_customer_invoices(self, sale):
        self.ensure_one()
        sale_sudo = sale.sudo()
        invoices = sale_sudo.invoice_ids.filtered(
            lambda inv: inv.move_type == "out_invoice" and inv.state != "cancel"
        )
        invoices |= sale_sudo.order_line.mapped("invoice_lines.move_id").filtered(
            lambda inv: inv.move_type == "out_invoice" and inv.state != "cancel"
        )
        invoice_model = self.env["account.move"].sudo()
        invoices |= invoice_model.search(
            [
                ("move_type", "=", "out_invoice"),
                ("state", "!=", "cancel"),
                ("invoice_line_ids.sale_line_ids.order_id", "=", sale_sudo.id),
            ]
        )
        invoices |= invoice_model.search(
            [
                ("move_type", "=", "out_invoice"),
                ("state", "!=", "cancel"),
                ("invoice_origin", "ilike", sale_sudo.name),
            ]
        )
        return invoices

    def _get_receipt_mode_label(self):
        self.ensure_one()
        name = (self.journal_id.name or "").upper()
        if "CASH" in name:
            return "CASH"
        if "UPI" in name or "QR" in name:
            return "UPI"
        if "CHEQUE" in name or "CHECK" in name:
            return "CHEQUE"
        if "PAYTM" in name:
            return "PAYTM"
        return name or "PAYMENT"

    def _get_receipt_amount_words(self):
        self.ensure_one()
        text = self.currency_id.amount_to_text(self.amount or 0.0) if self.currency_id else ""
        return (text or "").replace(",", "")

    def action_print_resonnocare_receipt(self):
        self.ensure_one()
        if not self._is_resonnocare_customer_receipt() or self.state not in ("in_process", "paid", "posted"):
            raise ValidationError("Receipt is available only for validated customer receipts.")
        report = self.env.ref("account.action_report_payment_receipt")
        return report.report_action(self)

    # @api.depends("journal_id")
    # def _compute_journal_flags(self):
    #     for rec in self:
    #         rec.is_upi_journal = False
    #         rec.is_cheque_journal = False
    #         rec.is_paytm_journal = False

    #         if not rec.journal_id:
    #             continue

    #         name = (rec.journal_id.name or "").lower()

    #         if "upi" in name or "qr" in name:
    #             rec.is_upi_journal = True

    #         if "cheque" in name or "check" in name:
    #             rec.is_cheque_journal = True

    #         if "paytm" in name:
    #             rec.is_paytm_journal = True

    def _check_excess_payment_diagnostic_contract(self):
        """
        Check for excess payment in diagnostic contracts and show alert.
        Works similarly to HA contract excess payment alert.
        """
        self.ensure_one()
        invoices = self.reconciled_invoice_ids
        if not invoices:
            return False
        
        categories = set(invoices.mapped("custom_invoice_category"))
        
        # Check if this is a diagnostic invoice
        if "DI" not in categories and "DC" not in categories:
            return False
        
        sale_orders = self._get_receipt_related_sale_orders(invoices)
        if not sale_orders:
            return False
        
        currency = self.currency_id or self.company_id.currency_id
        
        for sale in sale_orders:
            related_invoices = self._get_receipt_related_customer_invoices(sale)
            posted_invoices = related_invoices.filtered(lambda inv: inv.state == "posted")
            
            total_payable = sale.amount_total or 0.0
            paid_total = sum(
                inv._get_contract_advance_paid() if hasattr(inv, "_get_contract_advance_paid")
                else ((inv.amount_total or 0.0) - (inv.amount_residual or 0.0))
                for inv in posted_invoices
            )
            
            sale_currency = sale.currency_id or currency
            excess = paid_total - total_payable
            
            if sale_currency and excess > 0 and not sale_currency.is_zero(excess):
                return {
                    "type": "ir.actions.act_window",
                    "name": "Excess Payment Alert",
                    "res_model": "resonnocare.alert.dialog",
                    "view_mode": "form",
                    "target": "new",
                    "context": {
                        "alert_title": "Excess Payment - Diagnostic Contract",
                        "alert_message": f"Excess payment of {sale_currency.symbol} {excess:.2f} detected for diagnostic contract. Please verify the payment amount."
                    }
                }
        return False

    def _show_warning_dialog(self, title, message):
        """Show a warning dialog popup."""
        return {
            "type": "ir.actions.act_window",
            "name": title,
            "res_model": "resonnocare.alert.dialog",
            "view_mode": "form",
            "target": "new",
            "context": {
                "alert_title": title,
                "alert_message": message
            }
        }

    def unlink(self):
        """
        Override unlink to prevent deletion of validated payment receipts.
        Only allow deletion for draft/cancelled payments.
        """
        for payment in self:
            # Check if this is a Resonnocare customer receipt
            if payment._is_resonnocare_customer_receipt():
                # Prevent deletion if payment is in posted/paid/in_process state
                if payment.state in ("posted", "paid", "in_process"):
                    raise ValidationError(
                        f"Payment receipt '{payment.name}' is already validated ({payment.state.upper()}). "
                        "Validated and processed payment receipts cannot be deleted. "
                        "Please contact your administrator if you need to reverse this payment."
                    )
                
                # Prevent deletion if payment has been reconciled with invoices
                if payment.reconciled_invoice_ids:
                    raise ValidationError(
                        f"Payment receipt '{payment.name}' has been reconciled with invoices. "
                        "Reconciled payment receipts cannot be deleted. "
                        "Please cancel the related invoices first or contact your administrator."
                    )
        
        return super().unlink()

    def action_validate(self):

        _logger.info("action_validate called on account.payment")
        res = super().action_validate()

        # After payment validation, check for invoices and schedule appointments
        for payment in self:
            _logger.info(f"Payment {payment.id} state: {payment.state}")
            
            # Check for excess payment in diagnostic contracts
            excess_payment_action = payment._check_excess_payment_diagnostic_contract()
            if excess_payment_action:
                # Log the alert
                _logger.warning(f"Excess payment detected for diagnostic contract in payment {payment.id}")
            
            # Find invoices linked to this payment
            invoices = payment.reconciled_invoice_ids

            _logger.info(f"Reconciled invoices: {invoices.ids}")

            for invoice in invoices:
                _logger.info(f"Processing invoice {invoice.id} from payment {payment.id}")

                # Get sale orders from invoice lines
                sale_orders = invoice.invoice_line_ids.mapped(
                    "sale_line_ids.order_id"
                )

                _logger.info(f"Found sale orders: {sale_orders.ids}")

                if not sale_orders:
                    continue

                # Find draft appointments linked to these sale orders
                appointments = self.env["resonnocare.appointment"].search([
                    ("sale_order_id", "in", sale_orders.ids),
                    ("status", "=", "draft"),
                ])

                _logger.info(f"Found draft appointments: {appointments.ids}")

                # Schedule them
                appointments._schedule_after_payment()

        return res