from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


PAYMENT_MODE_SELECTION = [
    ("pos", "POS"),
    ("online", "Online"),
    ("cheque", "Cheque"),
    ("emi", "EMI"),
]

SUB_MODE_SELECTION = [
    ("upi", "UPI"),
    ("credit_card", "Credit Card"),
    ("debit_card", "Debit Card"),
    ("pay_by_link", "Pay by Link"),
    ("neft", "NEFT"),
    ("imps", "IMPS"),
    ("rtgs", "RTGS"),
    ("cheque_bank", "Bank Name"),
    ("no_cost_emi", "No Cost EMI"),
    ("regular_emi", "Regular EMI"),
]

PAY_TYPE_SELECTION = [
    ("dqr", "DQR"),
    ("sqr", "SQR"),
    ("mastercard", "Mastercard"),
    ("visa", "VISA"),
    ("rupay", "Rupay"),
    ("maestro", "Maestro"),
    ("diners", "Diners"),
    ("amex", "Amex"),
    ("card", "Card"),
]


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    payment_mode = fields.Selection(PAYMENT_MODE_SELECTION, string="Payment Mode")
    sub_mode = fields.Selection(SUB_MODE_SELECTION, string="Sub Mode")
    pay_type = fields.Selection(PAY_TYPE_SELECTION, string="Pay Type")
    reference_no = fields.Char(string="Reference No.")
    cheque_no = fields.Char(string="Cheque No.")
    cheque_date = fields.Date(string="Cheque Date")
    bank_id = fields.Many2one("res.bank", string="Bank Name")
    emi_partner_name = fields.Char(string="Partner Name")
    scheme_name = fields.Char(string="Scheme Name")

    @api.onchange("payment_mode")
    def _onchange_payment_mode(self):
        for wizard in self:
            wizard.sub_mode = False
            wizard.pay_type = False
            wizard.reference_no = False
            wizard.cheque_no = False
            wizard.cheque_date = False
            wizard.bank_id = False
            wizard.emi_partner_name = False
            wizard.scheme_name = False

    @api.onchange("sub_mode")
    def _onchange_sub_mode(self):
        for wizard in self:
            wizard.pay_type = False
            if wizard.sub_mode in ("neft", "imps", "rtgs", "cheque_bank",
                                   "no_cost_emi", "regular_emi"):
                wizard.reference_no = False

    @api.constrains(
        "payment_mode", "sub_mode", "pay_type", "reference_no",
        "cheque_no", "cheque_date", "bank_id", "emi_partner_name",
    )
    def _check_custom_payment_details(self):
        for wizard in self:
            if not wizard.payment_mode:
                continue
            if wizard.payment_mode == "pos":
                if not wizard.sub_mode:
                    raise ValidationError(_("Please select a Sub Mode for POS payments."))
                if wizard.sub_mode in ("upi", "credit_card", "debit_card", "pay_by_link") and not wizard.pay_type:
                    raise ValidationError(_("Please select a Pay Type for this POS payment."))
            elif wizard.payment_mode == "online":
                if wizard.sub_mode not in ("neft", "imps", "rtgs"):
                    raise ValidationError(_("For Online payments, select NEFT, IMPS, or RTGS."))
            elif wizard.payment_mode == "cheque":
                if not wizard.bank_id:
                    raise ValidationError(_("Please select the Bank Name for cheque payments."))
                if not wizard.cheque_no:
                    raise ValidationError(_("Please enter the Cheque No."))
                if not wizard.cheque_date:
                    raise ValidationError(_("Please enter the Cheque Date."))
            elif wizard.payment_mode == "emi":
                if wizard.sub_mode not in ("no_cost_emi", "regular_emi"):
                    raise ValidationError(_("For EMI payments, select No Cost EMI or Regular EMI."))
                if not wizard.emi_partner_name:
                    raise ValidationError(_("Please enter the Partner Name for EMI payments."))


    def _create_payment_vals_from_wizard(self, batch_result):
        vals = super()._create_payment_vals_from_wizard(batch_result)
        vals.update({
            "payment_mode": self.payment_mode,
            "sub_mode": self.sub_mode,
            "pay_type": self.pay_type,
            "reference_no": self.reference_no,
            "cheque_no": self.cheque_no,
            "cheque_date": self.cheque_date,
            "bank_id": self.bank_id.id if self.bank_id else False,
            "emi_partner_name": self.emi_partner_name,
            "scheme_name": self.scheme_name,
        })
        return vals


class AccountPayment(models.Model):
    _inherit = "account.payment"

    payment_mode = fields.Selection(PAYMENT_MODE_SELECTION, string="Payment Mode", copy=False)
    sub_mode = fields.Selection(SUB_MODE_SELECTION, string="Sub Mode", copy=False)
    pay_type = fields.Selection(PAY_TYPE_SELECTION, string="Pay Type", copy=False)
    reference_no = fields.Char(string="Reference No.", copy=False)
    cheque_no = fields.Char(string="Cheque No.", copy=False)
    cheque_date = fields.Date(string="Cheque Date", copy=False)
    bank_id = fields.Many2one("res.bank", string="Bank Name", copy=False)
    emi_partner_name = fields.Char(string="Partner Name", copy=False)
    scheme_name = fields.Char(string="Scheme Name", copy=False)
