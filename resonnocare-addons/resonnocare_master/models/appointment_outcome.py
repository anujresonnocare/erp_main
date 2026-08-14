# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ResonnocareAppointmentOutcome(models.Model):
    _name = "resonnocare.appointment.outcome"
    _description = "Appointment Outcome"
    _order = "sequence"
    _rec_name = "outcome"

    code = fields.Char(
        string="Outcome Code",
        required=True,
        copy=False,
        index=True,
        help="Unique code to identify the appointment outcome.",
    )
    outcome = fields.Char(
        string="Outcome",
        required=True,
        help="Label for the appointment outcome (e.g., Completed, Canceled).",
    )
    meaning = fields.Text(
        string="Meaning",
        help="Detailed explanation or significance of the outcome.",
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
        help="Order of outcomes in lists or dropdowns.",
    )
    active = fields.Boolean(
        string="Active",
        default=True,
    )

    _sql_constraints = [
        ("unique_outcome_code", "unique(code)", "Outcome Code must be unique.")
    ]
