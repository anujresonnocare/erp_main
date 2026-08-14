# -*- coding: utf-8 -*-
from odoo import models, fields

class ResonnocareDeviceType(models.Model):
    _name = "resonnocare.device.type"
    _description = "Resonnocare Device Type"
    _order = "name"

    name = fields.Char(string="Device Type", required=True)
    active = fields.Boolean(default=True)
