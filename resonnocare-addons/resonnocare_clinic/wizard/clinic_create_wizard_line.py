from odoo import models, fields


class ResonnocareClinicCreateWizardLine(models.TransientModel):
    _name = "resonnocare.clinic.create.wizard.line"
    _description = "Clinic Creation Diagnostic Pricing Line"

    wizard_id = fields.Many2one(
        "resonnocare.clinic.create.wizard",
        required=True,
        ondelete="cascade",
    )
    diagnostic_item_id = fields.Many2one(
        "resonnocare.diagnostic.item",
        # Keep optional in transient lines to avoid hard ORM failures
        # from accidental blank inline rows in the wizard list editor.
        required=False,
    )
    mrp = fields.Float(required=True)
