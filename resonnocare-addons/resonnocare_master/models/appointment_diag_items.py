from odoo import models, fields


class ResonnocareDiagnosticItem(models.Model):
    _name = "resonnocare.diagnostic.item"
    _description = "Diagnostic Item"
    _order = "sequence, id"
    _rec_name = "name"

    name = fields.Char(
        string="Diagnostic Test Name",
        required=True
    )

    code = fields.Char(
        string="Code",
        required=True
    )

    product_id = fields.Many2one(
        "product.product",
        string="Service Product",
        required=True,
        domain=[("type", "=", "service")],
        help="Service product used for billing this diagnostic test."
    )

    description = fields.Text(
        string="Description",
        help="Clinical description of the diagnostic test."
    )

    sequence = fields.Integer(
        string="Sequence",
        default=10
    )

    active = fields.Boolean(
        string="Active",
        default=True
    )

    is_diagnostic = fields.Boolean("Is Diagnostic")

    is_hearing_loss = fields.Boolean("Is Hearing Loss")

    appointment_type_id = fields.Many2one(
        "resonnocare.appointment.type",
        string="Appointment Type",
        help="Appointment type for which this diagnostic test is applicable."
    )

    

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Diagnostic Item code must be unique.')
    ]
