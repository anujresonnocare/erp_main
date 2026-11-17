# -*- coding: utf-8 -*-
from odoo import models, fields, api



class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_ear_mould = fields.Boolean(
        string="Ear Mould Product",
        help="Enable this for products that require Ear Mould Order Form during appointment billing flow.",
    )


    # Helper field to check if item_style_id is "Charger"
    is_charger_style = fields.Boolean(
        string="Is Charger Style", 
        compute="_compute_is_charger_style"
    )
    
    # Helper field to check if product is a Kit
    is_kit_product = fields.Boolean(
        string="Is Kit", 
        compute="_compute_is_kit_product"
    )

    @api.depends('item_style_id', 'item_style_id.name')
    def _compute_is_charger_style(self):
        for record in self:
            # Check if the item style name contains "charger" (case-insensitive)
            # Adjust the logic if you want an exact match or based on a specific code
            if record.item_style_id and record.item_style_id.name:
                record.is_charger_style = 'charger' in record.item_style_id.name.lower()
            else:
                record.is_charger_style = False

    @api.depends('display_name')
    def _compute_is_kit_product(self):
        for record in self:
            if "2+1" in record.display_name or "1+1" in record.display_name:
                record.is_kit_product = True