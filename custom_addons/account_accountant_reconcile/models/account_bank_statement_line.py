import logging

from dateutil.relativedelta import relativedelta

from odoo import fields, models

_logger = logging.getLogger(__name__)


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def _cron_try_auto_reconcile_statement_lines(self, batch_size=None, limit_time=0):
        """
        OVERWRITE: Replace the reconcilation method. Reconcile only based on amount and reference.
        """

        # Get all unreconciled bank statement lines
        st_line_ids = self.search(
            [
                ("is_reconciled", "=", False),
                (
                    "create_date",
                    ">",
                    fields.Datetime.now().date() - relativedelta(months=3),
                ),
            ]
        )

        # Get all unreconciled invoice lines
        unreconciled_lines = self.env["account.move.line"].search(
            [
                ("reconciled", "=", False),
                ("parent_state", "=", "posted"),
                ("is_account_reconcile", "=", True),
            ]
        )

        for st_line_id in st_line_ids:
            # Get payment reference and amount
            payment_ref = st_line_id.payment_ref
            amount = st_line_id.amount
            company_id = st_line_id.company_id

            # Find invoice line by reference and amount
            matching_lines = unreconciled_lines.filtered(
                lambda l: (l.name == payment_ref or l.move_name == payment_ref)
                and l.amount_residual == amount
                and l.company_id == company_id
            )

            # If only one invoice line is found, reconcile it
            if len(matching_lines) == 1:
                invoice_line = matching_lines[0]

                # Get the bank line
                bank_line = st_line_id.line_ids.filtered(lambda r: r.account_id.account_type == "asset_cash")

                # Ensure partner matches the invoice partner
                bank_line.write({"partner_id": invoice_line.partner_id.id})

                # Suspense line is the other line of the statement
                suspense_line = st_line_id.line_ids - bank_line

                # Ensure partner and account match the invoice line
                suspense_line.write(
                    {
                        "partner_id": invoice_line.partner_id.id,
                        "account_id": invoice_line.account_id.id,
                    }
                )

                # Reconcile the suspense and invoice line
                lines = suspense_line + invoice_line
                lines.reconcile()
                _logger.debug("Reconciled lines: %s", lines)
