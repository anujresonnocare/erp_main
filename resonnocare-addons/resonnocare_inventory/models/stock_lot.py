# -*- coding: utf-8 -*-
from odoo import models, fields


class StockLot(models.Model):
    _inherit = "stock.lot"

    warranty_start_date = fields.Date(string="Warranty Start Date")
    warranty_end_date = fields.Date(string="Warranty End Date")
