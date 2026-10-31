from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


PRODUCT_TYPE_SELECTION = [
    ("diagnostic", "Diagnostics"),
    ("device", "Device"),
    ("accessory", "Accessories"),
    ("repair", "Repairs"),
]

PAYMENT_TYPE_SELECTION = [
    ("regular", "Regular Payment"),
    ("down_payment", "Down Payment"),
    ("balance", "Balance Payment"),
]


BANK_SELECTION = [
    ("sbi", "State Bank of India (SBI)"),
    ("bob", "Bank of Baroda (BOB)"),
    ("boi", "Bank of India (BOI)"),
    ("bom", "Bank of Maharashtra (BOM)"),
    ("canara", "Canara Bank"),
    ("central", "Central Bank of India"),
    ("indian_bank", "Indian Bank"),
    ("iob", "Indian Overseas Bank (IOB)"),
    ("pnb", "Punjab National Bank (PNB)"),
    ("punjab_sind", "Punjab & Sind Bank"),
    ("uco", "UCO Bank"),
    ("union", "Union Bank of India"),
    ("hdfc", "HDFC Bank"),
    ("icici", "ICICI Bank"),
    ("axis", "Axis Bank"),
    ("kotak", "Kotak Mahindra Bank"),
    ("indusind", "IndusInd Bank"),
    ("idbi", "IDBI Bank"),
    ("idfc_first", "IDFC FIRST Bank"),
    ("federal", "Federal Bank"),
    ("yes_bank", "Yes Bank"),
    ("rbl", "RBL Bank"),
    ("south_indian", "South Indian Bank"),
    ("karnataka", "Karnataka Bank"),
    ("karur_vysya", "Karur Vysya Bank"),
    ("city_union", "City Union Bank"),
    ("dhanlaxmi", "Dhanlaxmi Bank"),
    ("tamilnad_mercantile", "Tamilnad Mercantile Bank"),
    ("csb", "CSB Bank"),
    ("jk_bank", "Jammu & Kashmir Bank"),
    ("bandhan", "Bandhan Bank"),
    ("dcb", "DCB Bank"),
    ("nainital", "Nainital Bank"),
    ("au_sfb", "AU Small Finance Bank"),
    ("equitas_sfb", "Equitas Small Finance Bank"),
    ("ujjivan_sfb", "Ujjivan Small Finance Bank"),
    ("jana_sfb", "Jana Small Finance Bank"),
    ("suryoday_sfb", "Suryoday Small Finance Bank"),
    ("utkarsh_sfb", "Utkarsh Small Finance Bank"),
    ("esaf_sfb", "ESAF Small Finance Bank"),
    ("fincare_sfb", "Fincare Small Finance Bank"),
    ("shivalik_sfb", "Shivalik Small Finance Bank"),
    ("ne_sfb", "North East Small Finance Bank"),
    ("airtel_pb", "Airtel Payments Bank"),
    ("ippb", "India Post Payments Bank"),
    ("fino_pb", "Fino Payments Bank"),
    ("paytm_pb", "Paytm Payments Bank"),
    ("nsdl_pb", "NSDL Payments Bank"),
    ("hsbc", "HSBC"),
    ("standard_chartered", "Standard Chartered Bank"),
    ("citibank", "Citibank"),
    ("dbs", "DBS Bank"),
    ("deutsche", "Deutsche Bank"),
    ("boa", "Bank of America"),
    ("barclays", "Barclays Bank"),
    ("bnp_paribas", "BNP Paribas"),
    ("jp_morgan", "J.P. Morgan Chase Bank"),
    ("mufg", "MUFG Bank"),
    ("societe_generale", "Société Générale"),
    ("credit_agricole", "Crédit Agricole"),
    ("qnb", "Qatar National Bank"),
    ("mizuho", "Mizuho Bank"),
    ("smbc", "Sumitomo Mitsui Banking Corporation (SMBC)"),
    ("scotiabank", "Bank of Nova Scotia"),
    ("anz", "Australia and New Zealand Banking Group (ANZ)"),
    ("saraswat_coop", "Saraswat Cooperative Bank"),
    ("cosmos_coop", "Cosmos Cooperative Bank"),
    ("abhyudaya_coop", "Abhyudaya Cooperative Bank"),
    ("bharat_coop", "Bharat Cooperative Bank"),
    ("shamrao_vithal_coop", "Shamrao Vithal Cooperative Bank"),
    ("tjsb_coop", "TJSB Sahakari Bank"),
    ("kalupur_coop", "Kalupur Commercial Cooperative Bank"),
    ("janata_sahakari", "Janata Sahakari Bank"),
]


from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    # ---------- Split lines ----------
    payment_line_ids = fields.One2many(
        "resonnocare.payment.line", "register_id", string="Payment Modes",
    )
    total_allocated = fields.Monetary(
        compute="_compute_total_allocated", store=True,
        currency_field="currency_id",
    )
    split_valid = fields.Boolean(compute="_compute_total_allocated", store=True)

    # ---------- Finance approval ----------
    finance_approval_required = fields.Boolean(
        compute="_compute_finance_approval", store=True,
    )
    finance_approved_by = fields.Many2one("res.users", readonly=True)
    finance_approved_on = fields.Datetime(readonly=True)
    show_finance_approval_button = fields.Boolean(
        compute="_compute_show_finance_approval_button",
    )
    can_create_payment = fields.Boolean(compute="_compute_can_create_payment")

    # ---------- Legacy fields (kept for old view + receipt) ----------
    upi_transaction_id = fields.Char(string="UPI Transaction ID")
    cheque_number = fields.Char(string="Cheque Number")
    cheque_date = fields.Date(string="Cheque Date")
    cheque_bank_name = fields.Char(string="Cheque Bank Name")
    paytm_txn_id = fields.Char(string="Paytm Transaction ID")

    is_upi_journal = fields.Boolean(compute="_compute_journal_flags", store=False)
    is_cheque_journal = fields.Boolean(compute="_compute_journal_flags", store=False)
    is_paytm_journal = fields.Boolean(compute="_compute_journal_flags", store=False)

    payment_already_exists = fields.Boolean(
        string="Payment Already Exists",
        compute="_compute_payment_already_exists",
        store=False,
    )
    confirm_subsequent_payment = fields.Boolean(default=False)


    mode_id = fields.Many2one(
        "resonnocare.payment.mode",
        string="Mode",
        compute="_compute_line_shortcuts",
        readonly=False,
    )

    submode_id = fields.Many2one(
        "resonnocare.payment.submode",
        string="Sub Mode",
        compute="_compute_line_shortcuts",
        readonly=False,
    )
    reference_no = fields.Char(
        compute="_compute_line_shortcuts", readonly=False, string="Reference No"
    )
    reference_date = fields.Date(
        compute="_compute_line_shortcuts", readonly=False, string="Payment Date"
    )
    bank_name = fields.Selection(
        selection=[
            ("sbi", "State Bank of India (SBI)"),
            ("bob", "Bank of Baroda (BOB)"),
            ("boi", "Bank of India (BOI)"),
            ("bom", "Bank of Maharashtra (BOM)"),
            ("canara", "Canara Bank"),
            # ... keep the same list you have in BANK_SELECTION
        ],
        compute="_compute_line_shortcuts",
        readonly=False,
        string="Bank Name",
    )
    emi_partner_id = fields.Many2one(
        "resonnocare.emi.partner",
        compute="_compute_line_shortcuts",
        readonly=False,
        string="EMI Partner",
    )
    emi_scheme_name = fields.Char(
        compute="_compute_line_shortcuts", readonly=False, string="Scheme Name"
    )
    is_cash_mode = fields.Boolean(
        compute="_compute_line_shortcuts", string="Is Cash"
    )

    @api.depends("payment_line_ids")
    def _compute_line_shortcuts(self):
        for rec in self:
            line = rec.payment_line_ids[:1]
            rec.mode_id = line.mode_id if line else False
            rec.submode_id = line.submode_id if line else False
            rec.reference_no = line.reference_no if line else False
            rec.reference_date = line.reference_date if line else False
            rec.bank_name = line.bank_name if line else False
            rec.emi_partner_id = line.emi_partner_id if line else False
            rec.emi_scheme_name = line.emi_scheme_name if line else False
            rec.is_cash_mode = line.is_cash_mode if line else False
            
    # ---------- Computes (legacy) ----------
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

    @api.depends("line_ids")
    def _compute_payment_already_exists(self):
        for rec in self:
            rec.payment_already_exists = False
            for line in rec.line_ids:
                invoice = line.move_id
                if not invoice:
                    continue
                if invoice.payment_state in ("paid", "in_payment", "partial"):
                    rec.payment_already_exists = True
                    break
                reconciled_payments = (
                    invoice.reconciled_payment_ids | invoice.matched_payment_ids
                )
                if reconciled_payments:
                    rec.payment_already_exists = True
                    break
                if hasattr(invoice, "_get_related_appointment"):
                    appointment = invoice._get_related_appointment()
                    if appointment:
                        sale = appointment._get_effective_sale_order()
                        if sale:
                            total_paid = appointment._get_total_paid_for_sale(sale)
                            if total_paid > 0.0:
                                rec.payment_already_exists = True
                                break

    # ---------- Computes (new split) ----------
    @api.depends("payment_line_ids.amount")
    def _compute_total_allocated(self):
        for rec in self:
            total = sum(rec.payment_line_ids.mapped("amount"))
            rec.total_allocated = total
            if not rec.payment_line_ids:
                rec.split_valid = False
            else:
                rec.split_valid = (
                    rec.currency_id.compare_amounts(total, rec.amount) == 0
                )

    @api.depends("payment_line_ids.mode_id.finance_approval_required")
    def _compute_finance_approval(self):
        for rec in self:
            rec.finance_approval_required = any(
                rec.payment_line_ids.mapped("mode_id.finance_approval_required")
            )

    @api.depends("finance_approval_required", "finance_approved_by")
    def _compute_show_finance_approval_button(self):
        is_finance = self.env.user.has_group(
            "resonnocare_payment_modes.group_finance_approver"
        )
        for rec in self:
            rec.show_finance_approval_button = bool(
                rec.finance_approval_required
                and not rec.finance_approved_by
                and is_finance
            )

    @api.depends(
        "payment_line_ids",
        "split_valid",
        "finance_approval_required",
        "finance_approved_by",
    )
    def _compute_can_create_payment(self):
        for rec in self:
            rec.can_create_payment = bool(
                rec.payment_line_ids
                and rec.split_valid
                and (
                    not rec.finance_approval_required
                    or rec.finance_approved_by
                )
            )

    @api.onchange("payment_line_ids")
    def _onchange_payment_lines_reset_approval(self):
        if self.finance_approved_by:
            self.finance_approved_by = False
            self.finance_approved_on = False

    # ---------- Applicability (split) ----------
    def _invoice_product_types(self):
        self.ensure_one()
        codes = set()
        for inv in self.line_ids.mapped("move_id"):
            for il in inv.invoice_line_ids.filtered(
                lambda l: l.product_id and not l.display_type
            ):
                item_type = getattr(il.product_id.product_tmpl_id, "item_type", False)
                if item_type:
                    codes.add(item_type)
        return codes

    def _payment_intent_type(self):
        self.ensure_one()
        for inv in self.line_ids.mapped("move_id"):
            appointment = False
            if hasattr(inv, "_get_related_appointment"):
                appointment = inv._get_related_appointment()
            if appointment and hasattr(appointment, "_get_effective_sale_order"):
                sale = appointment._get_effective_sale_order()
                if sale and hasattr(sale, "appointment_sale_type"):
                    st = (sale.appointment_sale_type or "").lower()
                    if "down" in st:
                        return "down_payment"
                    if "balance" in st:
                        return "balance"
                    return "regular"
        return "regular"

    def _check_applicability(self):
        self.ensure_one()
        product_types = self._invoice_product_types()
        intent = self._payment_intent_type()
        for line in self.payment_line_ids:
            mode = line.mode_id
            allowed_products = set(mode.applicable_product_types.mapped("code"))
            allowed_intents = set(mode.applicable_payment_types.mapped("code"))
            if allowed_products and product_types and not (product_types & allowed_products):
                raise ValidationError(
                    f"Mode '{mode.name}' is not applicable for the products in "
                    f"this invoice ({', '.join(sorted(product_types))})."
                )
            if allowed_intents and intent and intent not in allowed_intents:
                raise ValidationError(
                    f"Mode '{mode.name}' is not applicable for payment type '{intent}'."
                )

    # ---------- Button ----------
    def action_finance_approve(self):
        for rec in self:
            if not rec.finance_approval_required:
                continue
            if not self.env.user.has_group(
                "resonnocare_payment_modes.group_finance_approver"
            ):
                raise UserError("Only Finance Approvers can approve this payment.")
            rec.write({
                "finance_approved_by": self.env.user.id,
                "finance_approved_on": fields.Datetime.now(),
            })
        return {"type": "ir.actions.act_window_close"}

    # ---------- Legacy single-mode validation ----------
    def _validate_legacy_single_mode(self):
        if self.is_upi_journal and not self.upi_transaction_id:
            raise ValidationError("Please enter UPI Transaction ID.")
        if self.is_paytm_journal and not self.paytm_txn_id:
            raise ValidationError("Please enter Paytm Transaction ID.")
        if self.is_cheque_journal and (not self.cheque_number or not self.cheque_date):
            raise ValidationError("Please enter cheque details.")

    # ---------- Create payments (split-aware, with legacy fallback) ----------
    def _create_payments(self):
        self.ensure_one()

        # If no split lines were entered → legacy single-mode path
        if not self.payment_line_ids:
            self._validate_legacy_single_mode()
            payments = super()._create_payments()
            for payment in payments:
                move = payment.move_id or payment
                payment.write({"paytm_txn_id": self.paytm_txn_id})
                move.write({
                    "upi_transaction_id": self.upi_transaction_id,
                    "cheque_number": self.cheque_number,
                    "cheque_date": self.cheque_date,
                    "cheque_bank_name": self.cheque_bank_name,
                    "paytm_txn_id": self.paytm_txn_id,
                })
            return payments

        # Split-mode path
        if not self.split_valid:
            raise ValidationError(
                f"Allocated amount ({self.total_allocated}) must equal "
                f"the total ({self.amount})."
            )
        if self.finance_approval_required and not self.finance_approved_by:
            raise ValidationError(
                "Finance approval is required before creating payments."
            )

        self._check_applicability()
        for line in self.payment_line_ids:
            line.validate_line()

        payments = self.env["account.payment"]
        original_amount = self.amount
        original_journal = self.journal_id
        original_pml = self.payment_method_line_id

        try:
            for line in self.payment_line_ids:
                journal = line.mode_id.default_journal_id or original_journal
                pml = line.mode_id.default_payment_method_line_id or original_pml
                if not journal:
                    raise UserError(
                        f"No journal configured for mode '{line.mode_id.name}' "
                        f"and none selected on the wizard."
                    )
                self.write({
                    "amount": line.amount,
                    "journal_id": journal.id,
                    "payment_method_line_id": pml.id if pml else False,
                })
                payment = super(
                    AccountPaymentRegister,
                    self.with_context(resonnocare_payment_line_id=line.id),
                )._create_payments()

                payment.write({
                    "resonnocare_payment_mode_id": line.mode_id.id,
                    "resonnocare_payment_submode_id": line.submode_id.id,
                })
                move = payment.move_id
                if move:
                    move.write({
                        "resonnocare_payment_mode_id": line.mode_id.id,
                        "resonnocare_payment_submode_id": line.submode_id.id,
                        "upi_transaction_id": (
                            line.reference_no
                            if line.submode_id and line.submode_id.submode_group == "upi"
                            else False
                        ),
                        "paytm_txn_id": (
                            line.reference_no
                            if line.submode_id
                            and "paytm" in (line.submode_id.code or "").lower()
                            else False
                        ),
                        "cheque_number": line.cheque_number or False,
                        "cheque_date": line.cheque_date or False,
                        "cheque_bank_name": line.bank_name or False,
                    })
                payments |= payment
        finally:
            self.write({
                "amount": original_amount,
                "journal_id": original_journal.id if original_journal else False,
                "payment_method_line_id": original_pml.id if original_pml else False,
            })
        return payments



class ResonnocareEmiPartner(models.Model):
    _name = "resonnocare.emi.partner"
    _description = "EMI Partner"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)






class ResonnocarePaymentMode(models.Model):
    _name = "resonnocare.payment.mode"
    _description = "Payment Mode"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    finance_approval_required = fields.Boolean(
        string="Finance Approval Required",
        help="If checked, a finance user must approve the register before "
             "payments can be created when this mode is used.",
    )
    applicable_product_types = fields.Many2many(
        "resonnocare.product.type",
        string="Applicable for Product Types",
    )
    applicable_payment_types = fields.Many2many(
        "resonnocare.payment.type",
        string="Applicable for Payment Types",
    )

    default_journal_id = fields.Many2one(
        "account.journal",
        string="Default Journal",
        help="Journal used when creating the payment for this mode.",
    )
    default_payment_method_line_id = fields.Many2one(
        "account.payment.method.line",
        string="Default Payment Method",
        domain="[('journal_id', '=', default_journal_id)]",
    )

    submode_ids = fields.One2many(
        "resonnocare.payment.submode", "mode_id", string="Sub Modes"
    )

    _sql_constraints = [
        ("code_uniq", "unique(code)", "Payment mode code must be unique."),
    ]


class ResonnocareProductType(models.Model):
    _name = "resonnocare.product.type"
    _description = "Product Type (for payment applicability)"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)

    _sql_constraints = [
        ("code_uniq", "unique(code)", "Product type code must be unique."),
    ]


class ResonnocarePaymentType(models.Model):
    _name = "resonnocare.payment.type"
    _description = "Payment Type (for payment applicability)"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)

    _sql_constraints = [
        ("code_uniq", "unique(code)", "Payment type code must be unique."),
    ]



class ResonnocarePaymentSubmode(models.Model):
    _name = "resonnocare.payment.submode"
    _description = "Payment Sub Mode"
    _order = "sequence, id"

    mode_id = fields.Many2one(
        "resonnocare.payment.mode", required=True, ondelete="cascade"
    )
    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    submode_group = fields.Selection(
        [
            ("upi", "UPI"),
            ("card", "Card"),
            ("bank_transfer", "Bank Transfer"),
            ("pay_by_link", "Pay by Link"),
            ("emi", "EMI"),
            ("other", "Other"),
        ],
        default="other",
        required=True,
    )

    needs_reference_no = fields.Boolean(string="Needs Reference No")
    needs_reference_date = fields.Boolean(string="Needs Reference Date")
    needs_bank_name = fields.Boolean(string="Needs Bank Name")
    needs_cheque = fields.Boolean(string="Needs Cheque Details")
    needs_emi_details = fields.Boolean(string="Needs EMI Details")

    _sql_constraints = [
        (
            "mode_code_uniq",
            "unique(mode_id, code)",
            "Sub mode code must be unique per payment mode.",
        ),
    ]


class ResonnocarePaymentDenomination(models.TransientModel):
    _name = "resonnocare.payment.denomination"
    _description = "Cash Denomination"

    line_id = fields.Many2one(
        "resonnocare.payment.line", required=True, ondelete="cascade"
    )
    currency_id = fields.Many2one(related="line_id.currency_id")

    denomination = fields.Integer(required=True)
    count = fields.Integer(default=0)
    subtotal = fields.Monetary(
        compute="_compute_subtotal", store=True, currency_field="currency_id"
    )

    @api.depends("denomination", "count")
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = (rec.denomination or 0) * (rec.count or 0)




class ResonnocarePaymentLine(models.TransientModel):
    _name = "resonnocare.payment.line"
    _description = "Payment Register Line"

    register_id = fields.Many2one(
        "account.payment.register", required=True, ondelete="cascade"
    )
    currency_id = fields.Many2one(related="register_id.currency_id")

    mode_id = fields.Many2one("resonnocare.payment.mode", required=True)
    submode_id = fields.Many2one(
        "resonnocare.payment.submode",
        domain="[('mode_id', '=', mode_id)]",
    )

    amount = fields.Monetary(currency_field="currency_id", required=True)

    # Detail fields (shown based on submode flags)
    reference_no = fields.Char(string="Reference No")
    reference_date = fields.Date(string="Payment Date")
    cheque_number = fields.Char(string="Cheque No")
    cheque_date = fields.Date(string="Cheque Date")
    bank_name = fields.Selection(BANK_SELECTION, string="Bank Name")
    emi_partner_id = fields.Many2one("resonnocare.emi.partner", string="EMI Partner")
    emi_scheme_name = fields.Char(string="Scheme Name")

    # Cash denomination lines
    denomination_ids = fields.One2many(
        "resonnocare.payment.denomination", "line_id", string="Denominations"
    )
    denomination_total = fields.Monetary(
        compute="_compute_denomination_total",
        store=True,
        currency_field="currency_id",
    )

    is_cash_mode = fields.Boolean(compute="_compute_is_cash_mode")

    @api.depends("denomination_ids.subtotal")
    def _compute_denomination_total(self):
        for rec in self:
            rec.denomination_total = sum(rec.denomination_ids.mapped("subtotal"))

    @api.depends("mode_id.code")
    def _compute_is_cash_mode(self):
        for rec in self:
            rec.is_cash_mode = rec.mode_id.code == "cash"

    @api.onchange("mode_id")
    def _onchange_mode_id(self):
        if self.mode_id:
            self.submode_id = False

    def validate_line(self):
        self.ensure_one()
        sub = self.submode_id
        if not sub:
            raise ValidationError("Please select a Sub Mode for every payment line.")

        if sub.needs_reference_no and not self.reference_no:
            raise ValidationError(
                f"{sub.name}: Reference No is required."
            )
        if sub.needs_reference_date and not self.reference_date:
            raise ValidationError(
                f"{sub.name}: Payment Date is required."
            )
        if sub.needs_bank_name and not self.bank_name:
            raise ValidationError(
                f"{sub.name}: Bank Name is required."
            )
        if sub.needs_cheque:
            if not self.cheque_number:
                raise ValidationError("Cheque: Cheque No is required.")
            if not self.cheque_date:
                raise ValidationError("Cheque: Cheque Date is required.")
            if not self.bank_name:
                raise ValidationError("Cheque: Bank Name is required.")
        if sub.needs_emi_details:
            if not self.emi_partner_id:
                raise ValidationError("EMI: Partner is required.")
            if not self.emi_scheme_name:
                raise ValidationError("EMI: Scheme Name is required.")

        if self.is_cash_mode:
            total = sum(self.denomination_ids.mapped("subtotal"))
            if self.currency_id.compare_amounts(total, self.amount) != 0:
                raise ValidationError(
                    f"Cash: Denomination total ({total}) must equal the "
                    f"cash amount ({self.amount})."
                )



class AccountPayment(models.Model):
    _inherit = "account.payment"

    resonnocare_payment_mode_id = fields.Many2one(
        "resonnocare.payment.mode", string="Payment Mode"
    )
    resonnocare_payment_submode_id = fields.Many2one(
        "resonnocare.payment.submode", string="Payment Sub Mode"
    )

    def action_print_resonnocare_receipt(self):
        self.ensure_one()
        return self.env.ref(
            "resonnocare_payment_modes.action_report_payment_receipt"
        ).report_action(self)



class AccountMove(models.Model):
    _inherit = "account.move"

    upi_transaction_id = fields.Char(string="UPI Transaction ID")
    paytm_txn_id = fields.Char(string="Paytm Transaction ID")
    cheque_number = fields.Char(string="Cheque Number")
    cheque_date = fields.Date(string="Cheque Date")
    cheque_bank_name = fields.Char(string="Cheque Bank Name")
    resonnocare_payment_mode_id = fields.Many2one(
        "resonnocare.payment.mode", string="Payment Mode"
    )
    resonnocare_payment_submode_id = fields.Many2one(
        "resonnocare.payment.submode", string="Payment Sub Mode"
    )    