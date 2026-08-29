# -*- coding: utf-8 -*-
from odoo import models

class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_print_payment_voucher(self):
        self.ensure_one()
        return self.env.ref(
            "account_payment_voucher.action_payment_voucher_report"
        ).report_action(self)


    def action_print_payment_receipt(self):
        self.ensure_one()
        return self.env.ref(
            "account.action_report_payment_receipt"
        ).report_action(self)
        