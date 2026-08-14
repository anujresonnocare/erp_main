# -*- coding: utf-8 -*-
from odoo import models, fields


class ResonnocareDevice(models.Model):
    _name = "resonnocare.device"
    _description = "Resonnocare Device"
    _order = "device_code"

    device_code = fields.Char(
        string="Device Code / Serial No", required=True, copy=False
    )

    name = fields.Char(string="Device Name", required=True)

    device_type_id = fields.Many2one(
        "resonnocare.device.type", string="Device Type", required=True
    )

    clinic_id = fields.Many2one("resonnocare.clinic", string="Clinic", required=True)

    status = fields.Selection(
        [
            ("available", "Available"),
            ("assigned", "Assigned"),
            ("maintenance", "Under Maintenance"),
            ("retired", "Retired"),
        ],
        string="Status",
        default="available",
        required=True,
    )

    notes = fields.Text(string="Internal Notes")

    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("device_code_unique", "unique(device_code)", "Device Code must be unique.")
    ]
