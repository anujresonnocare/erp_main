# -*- coding: utf-8 -*-
from odoo import models, fields


class StockLot(models.Model):
    _inherit = "stock.lot"

    is_left_ear = fields.Boolean(string="Is Left Ear")
    is_right_ear = fields.Boolean(string="Is Right Ear")

    warranty_start_date = fields.Date(string="Warranty Start Date")
    warranty_end_date = fields.Date(string="Warranty End Date")
