# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ResonnocareAppointmentType(models.Model):
    _name = "resonnocare.appointment.type"
    _description = "Appointment Type"
    _order = "sequence, id"
    _rec_name = "name"

    name = fields.Char(string="Appointment Type", required=True)

    code = fields.Char(string="Appointment Code", readonly=True, copy=False, index=True)

    duration = fields.Integer(string="Duration (Minutes)", default=30, required=True)
    sale_type = fields.Selection(
        [("service", "Service"), ("device", "Device")],
        string="Sale Type",
        required=True,
        default="service",
    )

    sequence = fields.Integer(default=10)
    description = fields.Text(string="Description")
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("unique_appointment_code", "unique(code)", "Appointment Code must be unique."),
        ("unique_appointment_name", "unique(name)", "Appointment Type name must be unique."),
    ]

    @api.model
    def create(self, vals):
        if not vals.get("code"):
            seq = self.env["ir.sequence"].next_by_code("resonnocare.appointment.type")
            if not seq:
                raise ValidationError("Appointment Type sequence is missing.")
            vals["code"] = seq

        return super().create(vals)

    @api.constrains("name")
    def _check_name_unique_case_insensitive(self):
        for rec in self:
            normalized = " ".join((rec.name or "").split()).strip().lower()
            if not normalized:
                continue
            duplicates = self.search(
                [("id", "!=", rec.id), ("name", "!=", False)]
            ).filtered(
                lambda r: " ".join((r.name or "").split()).strip().lower() == normalized
            )
            if duplicates:
                raise ValidationError(
                    "Appointment Type name must be unique (case-insensitive)."
                )
