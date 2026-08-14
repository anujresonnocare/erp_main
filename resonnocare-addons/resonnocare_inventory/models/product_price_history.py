# -*- coding: utf-8 -*-
from odoo import models, fields


class ResonnocareProductPriceHistory(models.Model):
    _name = "resonnocare.product.price.history"
    _description = "Product Price History"
    _order = "change_date desc, id desc"

    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Product",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        index=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )
    old_list_price = fields.Float(string="Old Sales Price")
    new_list_price = fields.Float(string="New Sales Price")
    old_standard_price = fields.Float(string="Old Cost")
    new_standard_price = fields.Float(string="New Cost")
    changed_by = fields.Many2one(
        "res.users",
        string="Changed By",
        default=lambda self: self.env.user,
        readonly=True,
    )
    change_date = fields.Datetime(
        string="Changed On",
        default=fields.Datetime.now,
        readonly=True,
    )
    change_note = fields.Char(string="Note")
    description = fields.Text(string="Description")
