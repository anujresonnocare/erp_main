from odoo import models, fields


class ResonnocareClinicDiagnosticPriceHistory(models.Model):
    _name = "resonnocare.clinic.diagnostic.price.history"
    _description = "Clinic Diagnostic Price History"
    _order = "change_date desc, id desc"

    clinic_diagnostic_id = fields.Many2one(
        "resonnocare.clinic.diagnostic",
        string="Clinic Diagnostic Price",
        required=True,
        ondelete="cascade",
        index=True,
    )
    clinic_id = fields.Many2one(
        "resonnocare.clinic",
        string="Clinic",
        related="clinic_diagnostic_id.clinic_id",
        store=True,
        readonly=True,
    )
    diagnostic_item_id = fields.Many2one(
        "resonnocare.diagnostic.item",
        string="Diagnostic Item",
        related="clinic_diagnostic_id.diagnostic_item_id",
        store=True,
        readonly=True,
    )
    old_mrp = fields.Float(string="Old MRP", required=True)
    new_mrp = fields.Float(string="New MRP", required=True)
    changed_by_id = fields.Many2one(
        "res.users",
        string="Changed By",
        default=lambda self: self.env.user,
        readonly=True,
    )
    change_date = fields.Datetime(
        string="Changed On",
        default=fields.Datetime.now,
        readonly=True,
    )
    change_note = fields.Char(string="Note")
