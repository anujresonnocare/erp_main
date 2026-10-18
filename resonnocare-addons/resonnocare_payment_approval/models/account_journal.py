from odoo import models, fields

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    requires_payment_approval = fields.Boolean(
        string="Require Payment Approval",
        help="If checked, payments made through this journal will remain in draft and wait for Finance approval."
    )