# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_ear_mould = fields.Boolean(
        string="Ear Mould Product",
        help="Enable this for products that require Ear Mould Order Form during appointment billing flow.",
    )
