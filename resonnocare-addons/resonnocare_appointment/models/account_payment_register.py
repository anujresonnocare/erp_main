from odoo import models, fields, api
from odoo.exceptions import ValidationError

class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    upi_transaction_id = fields.Char(string="UPI Transaction ID")
    cheque_number = fields.Char(string="Cheque Number")
    cheque_date = fields.Date(string="Cheque Date")
    # cheque_bank_name = fields.Char(string="Cheque Bank Name")

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
    ], string='Bank Name', required=True)
    paytm_txn_id = fields.Char(string="Paytm Transaction ID")

    is_upi_journal = fields.Boolean(compute="_compute_journal_flags", store=False)
    is_cheque_journal = fields.Boolean(compute="_compute_journal_flags", store=False)
    is_paytm_journal = fields.Boolean(compute="_compute_journal_flags", store=False)

    @api.depends("journal_id")
    def _compute_journal_flags(self):
        for rec in self:
            rec.is_upi_journal = False
            rec.is_cheque_journal = False
            rec.is_paytm_journal = False

            if not rec.journal_id:
                continue

            name = (rec.journal_id.name or "").lower()

            if "upi" in name or "qr" in name:
                rec.is_upi_journal = True

            if "cheque" in name or "check" in name:
                rec.is_cheque_journal = True

            if "paytm" in name:
                rec.is_paytm_journal = True

    payment_already_exists = fields.Boolean(
        string="Payment Already Exists",
        compute="_compute_payment_already_exists",
        store=False,
    )
    confirm_subsequent_payment = fields.Boolean(
        string="Confirm Subsequent Payment",
        default=False,
    )

    @api.depends("line_ids")
    def _compute_payment_already_exists(self):
        for rec in self:
            rec.payment_already_exists = False
            for line in rec.line_ids:
                invoice = line.move_id
                if not invoice:
                    continue
                
                # Check if invoice itself is paid or partially paid
                if invoice.payment_state in ('paid', 'in_payment', 'partial'):
                    rec.payment_already_exists = True
                    break
                
                # Check if invoice has reconciled/matched payments
                reconciled_payments = invoice.reconciled_payment_ids | invoice.matched_payment_ids
                if reconciled_payments:
                    rec.payment_already_exists = True
                    break

                # Check related appointment payments
                if hasattr(invoice, '_get_related_appointment'):
                    appointment = invoice._get_related_appointment()
                    if appointment:
                        sale = appointment._get_effective_sale_order()
                        if sale:
                            total_paid = appointment._get_total_paid_for_sale(sale)
                            if total_paid > 0.0:
                                rec.payment_already_exists = True
                                break

    def _create_payments(self):
        if self.is_upi_journal and not self.upi_transaction_id:
            raise ValidationError("Please enter UPI Transaction ID.")

        if self.is_paytm_journal and not self.paytm_txn_id:
            raise ValidationError("Please enter Paytm Transaction ID.")

        if self.is_cheque_journal:
            if not self.cheque_number or not self.cheque_date:
                raise ValidationError("Please enter cheque details.")

        # if self.payment_already_exists and not self.confirm_subsequent_payment:
        #     raise ValidationError(
        #         "⚠️ Warning: A payment has already been processed for this appointment/invoice. "
        #         "If you are sure you want to register another payment, please check the "
        #         "'Confirm Subsequent Payment' box before clicking Create Payment."
        #     )

        payments = super()._create_payments()

        # IMPORTANT FIX: write on account.move, not account.payment
        for payment in payments:
            move = payment.move_id or payment  # safety

            payment.write({
                "paytm_txn_id": self.paytm_txn_id,
            })
            move.write({
                "upi_transaction_id": self.upi_transaction_id,
                "cheque_number": self.cheque_number,
                "cheque_date": self.cheque_date,
                "cheque_bank_name": self.cheque_bank_name,
                "paytm_txn_id": self.paytm_txn_id,
            })

        return payments
