from odoo import models, fields, api
from odoo.exceptions import ValidationError

class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    upi_transaction_id = fields.Char(string="UPI Transaction ID")
    cheque_number = fields.Char(string="Cheque Number")
    cheque_date = fields.Date(string="Cheque Date")
    cheque_bank_name = fields.Char(string="Cheque Bank Name")
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
