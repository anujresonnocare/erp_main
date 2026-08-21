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

    is_upi_journal = fields.Boolean(compute="_compute_journal_flags", store=False)
    is_cheque_journal = fields.Boolean(compute="_compute_journal_flags", store=False)
    is_paytm_journal = fields.Boolean(compute="_compute_journal_flags", store=False)

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