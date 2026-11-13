from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    # ------------------------------------------------------------------
    # MASTER FIELD
    # ------------------------------------------------------------------
    payment_mode = fields.Selection([
        ("POS", "POS"),
        ("Online", "Online"),
        ("Cheque", "Cheque"),
        ("EMI", "EMI"),
    ], string="Payment Mode")

    # ------------------------------------------------------------------
    # SUB MODES
    # ------------------------------------------------------------------
    sub_mode_pos = fields.Selection([
        ("UPI", "UPI"),
        ("Credit_Card", "Credit Card"),
        ("Debit_Card", "Debit Card"),
        ("Pay_by_Link", "Pay by Link"),
    ], string="Sub Mode (POS)")

    sub_mode_online = fields.Selection([
        ("NEFT", "NEFT"),
        ("IMPS", "IMPS"),
        ("RTGS", "RTGS"),
    ], string="Sub Mode (Online)")

    sub_mode_emi = fields.Selection([
        ("No_Cost_EMI", "No Cost EMI"),
        ("Regular_EMI", "Regular EMI"),
    ], string="Sub Mode (EMI)")

    # ------------------------------------------------------------------
    # PAY TYPES
    # ------------------------------------------------------------------
    pay_type_upi = fields.Selection([
        ("DQR", "DQR"),
        ("SQR", "SQR"),
    ], string="UPI Type")

    pay_type_card = fields.Selection([
        ("Mastercard", "Mastercard"),
        ("VISA", "VISA"),
        ("Rupay", "Rupay"),
        ("Maestro", "Maestro"),
        ("Diners", "Diners"),
        ("Amex", "Amex"),
    ], string="Card Type")

    pay_type_link = fields.Selection([
        ("Card", "Card"),
    ], string="Pay by Link Type")

    # ------------------------------------------------------------------
    # SHARED DETAILS
    # ------------------------------------------------------------------
    reference_no = fields.Char("Reference No")
    payment_date = fields.Date("Payment Date", default=fields.Date.context_today)

    cheque_no = fields.Char("Cheque No")
    cheque_date = fields.Date("Cheque Date")
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

    # EMI only
    partner_name = fields.Selection([
        ("Paytm", "Paytm"),
        ("HDFC", "HDFC"),
        ("Shopse", "Shopse"),
        ("FIBER", "FIBER"),
    ], string="Partner Name")
    scheme_name = fields.Char("Scheme Name")

    # ------------------------------------------------------------------
    # FLAGS (derived from payment_mode / sub_mode_pos — no journal name lookup)
    # ------------------------------------------------------------------
    is_pos_upi = fields.Boolean(compute="_compute_flags", store=False)
    is_pos_card = fields.Boolean(compute="_compute_flags", store=False)
    is_pos_link = fields.Boolean(compute="_compute_flags", store=False)
    is_online = fields.Boolean(compute="_compute_flags", store=False)
    is_cheque = fields.Boolean(compute="_compute_flags", store=False)
    is_emi = fields.Boolean(compute="_compute_flags", store=False)

    @api.depends("payment_mode", "sub_mode_pos")
    def _compute_flags(self):
        for rec in self:
            rec.is_pos_upi = rec.payment_mode == "POS" and rec.sub_mode_pos == "UPI"
            rec.is_pos_card = rec.payment_mode == "POS" and rec.sub_mode_pos in ("Credit_Card", "Debit_Card")
            rec.is_pos_link = rec.payment_mode == "POS" and rec.sub_mode_pos == "Pay_by_Link"
            rec.is_online = rec.payment_mode == "Online"
            rec.is_cheque = rec.payment_mode == "Cheque"
            rec.is_emi = rec.payment_mode == "EMI"

    # ------------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------------
    def _validate_payment_mode_fields(self):
        for rec in self:
            if not rec.payment_mode:
                raise ValidationError("Please select a Payment Mode.")

            if rec.payment_mode == "POS":
                if not rec.sub_mode_pos:
                    raise ValidationError("Please select a POS Sub Mode.")
                if rec.sub_mode_pos == "UPI" and not rec.pay_type_upi:
                    raise ValidationError("Please select a UPI Type (DQR / SQR).")
                if rec.sub_mode_pos in ("Credit_Card", "Debit_Card") and not rec.pay_type_card:
                    raise ValidationError("Please select a Card Type.")
                if rec.sub_mode_pos == "Pay_by_Link" and not rec.pay_type_link:
                    raise ValidationError("Please select a Pay by Link Type.")

            if rec.payment_mode == "Online":
                if not rec.sub_mode_online:
                    raise ValidationError("Please select an Online Sub Mode (NEFT / IMPS / RTGS).")
                if not rec.reference_no:
                    raise ValidationError("Please enter the Reference No.")
                if not rec.payment_date:
                    raise ValidationError("Please enter the Payment Date.")

            if rec.payment_mode == "Cheque":
                if not rec.cheque_bank_name:
                    raise ValidationError("Please select the Bank Name.")
                if not rec.cheque_no:
                    raise ValidationError("Please enter the Cheque No.")
                if not rec.cheque_date:
                    raise ValidationError("Please enter the Cheque Date.")

            if rec.payment_mode == "EMI":
                if not rec.sub_mode_emi:
                    raise ValidationError("Please select an EMI Sub Mode.")
                if not rec.partner_name:
                    raise ValidationError("Please select the Partner Name.")
                if not rec.cheque_no:
                    raise ValidationError("Please enter the Cheque No.")
                if not rec.cheque_date:
                    raise ValidationError("Please enter the Cheque Date.")

    def _create_payments(self):
        self._validate_payment_mode_fields()
        payments = super()._create_payments()

        for payment in payments:
            payment.write({
                "payment_mode":      self.payment_mode,
                "sub_mode_pos":      self.sub_mode_pos,
                "sub_mode_online":   self.sub_mode_online,
                "sub_mode_emi":      self.sub_mode_emi,
                "pay_type_upi":      self.pay_type_upi,
                "pay_type_card":     self.pay_type_card,
                "pay_type_link":     self.pay_type_link,
                "reference_no":      self.reference_no,
                "payment_date":      self.payment_date,
                "cheque_no":         self.cheque_no,
                "cheque_date":       self.cheque_date,
                "cheque_bank_name":  self.cheque_bank_name,
                "partner_name":      self.partner_name,
                "scheme_name":       self.scheme_name,
            })

        return payments