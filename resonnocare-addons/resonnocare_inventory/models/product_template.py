# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools.float_utils import float_compare


class ProductTemplate(models.Model):
    _inherit = "product.template"

    brand = fields.Char(string="Brand")
    can_number = fields.Char(
        string="CAN Number",
        help="CAN number used for ear mould products.",
    )
    rechargeable = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        string="Rechargeable",
        default="no",
    )
    item_type = fields.Selection(
        [
            ("ha", "HA"),
            ("accessories", "Accessories"),
            ("battery", "Battery"),
            ("receiver", "Receiver"),
            ("v2_receiver", "V2 Receiver"),
            ("eartips", "Eartips"),
            ("sleeve", "Sleeve"),
            ("mould", "Mould"),
            ("btl_bend", "BTL Bend"),
            ("dry_kit", "Dry Kit"),
            ("wax_guard", "Wax Guard"),
            ("cleaning_kit", "Cleaning Kit"),
            ("consumable", "Consumable"),
            ("equipment", "Equipment"),
        ],
        string="Item Type",
    )
    item_style = fields.Char(string="Item Style")
    # item_category = fields.Char(string="Item Category")
    item_category = fields.Selection(
        [
            ("hearing_device", "Hearing Device"),
            ("diagnostic_services", "Diagnostic Services"),
            ("accessories_sale", "Accessories Sale"),
            ("repair_services", "Repair Services"),
            ("other_products", "Other Products"),
            ("other_services", "Other Services"),
            ("cat_1", "Cat 1"),
            ("cat_2", "Cat 2"),
            ("cat_3", "Cat 3"),
            ("cat_4", "Cat 4"),
            ("cat_5", "Cat 5"),
            ("cat_6", "Cat 6"),
            ("cat_7", "Cat 7"),
            ("cat_c", "Cat C"),
            ("cat_d", "Cat D"),
            ("cat_e", "Cat E"),
        ],
        string="Item Category",
        default="hearing_device",
    )
    hearing_aid_color = fields.Char(string="Color")
    warranty_months = fields.Integer(
        string="Warranty (Months)",
        help="Warranty duration in months from the sale date.",
    )
    manufacturer_id = fields.Many2one(
        "res.partner",
        string="Manufacturer",
        domain=[("supplier_rank", ">", 0)],
    )
    price_history_ids = fields.One2many(
        "resonnocare.product.price.history",
        "product_tmpl_id",
        string="Price History",
    )
    price_history_count = fields.Integer(
        string="Price History Count",
        compute="_compute_price_history_count",
        groups="resonnocare_base.group_resonnocare_super_admin",
    )

    @api.depends("price_history_ids")
    def _compute_price_history_count(self):
        counts = (
            self.env["resonnocare.product.price.history"]
            .sudo()
            .read_group(
                [("product_tmpl_id", "in", self.ids)],
                ["product_tmpl_id"],
                ["product_tmpl_id"],
            )
        )
        mapped = {item["product_tmpl_id"][0]: item["product_tmpl_id_count"] for item in counts}
        for product in self:
            product.price_history_count = mapped.get(product.id, 0)

    def action_open_price_history(self):
        self.ensure_one()
        action = self.env.ref(
            "resonnocare_inventory.action_resonnocare_product_price_history"
        ).read()[0]
        action["domain"] = [("product_tmpl_id", "=", self.id)]
        action["context"] = {
            "default_product_tmpl_id": self.id,
            "search_default_product": 1,
        }
        return action

    def _price_history_needs_update(self, old_list_price, old_standard_price):
        rounding = self.currency_id.rounding or 0.01
        list_changed = (
            float_compare(old_list_price, self.list_price, precision_rounding=rounding) != 0
        )
        cost_changed = (
            float_compare(old_standard_price, self.standard_price, precision_rounding=rounding)
            != 0
        )
        return list_changed or cost_changed

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if self.env.context.get("skip_price_history"):
            return records
        history_vals = []
        for product in records:
            history_vals.append(
                {
                    "product_tmpl_id": product.id,
                    "company_id": product.company_id.id or self.env.company.id,
                    "old_list_price": product.list_price,
                    "new_list_price": product.list_price,
                    "old_standard_price": product.standard_price,
                    "new_standard_price": product.standard_price,
                    "change_note": "Initial price",
                }
            )
        if history_vals:
            self.env["resonnocare.product.price.history"].sudo().create(history_vals)
        return records

    def write(self, vals):
        if self.env.context.get("skip_price_history"):
            return super().write(vals)
        track = any(key in vals for key in ("list_price", "standard_price"))
        if not track:
            return super().write(vals)

        old_values = {
            product.id: (
                product.list_price,
                product.standard_price,
                product.company_id.id or self.env.company.id,
            )
            for product in self
        }
        res = super().write(vals)
        history_vals = []
        for product in self:
            old_list_price, old_standard_price, company_id = old_values.get(
                product.id,
                (
                    product.list_price,
                    product.standard_price,
                    product.company_id.id or self.env.company.id,
                ),
            )
            if not product._price_history_needs_update(old_list_price, old_standard_price):
                continue
            history_vals.append(
                {
                    "product_tmpl_id": product.id,
                    "company_id": company_id,
                    "old_list_price": old_list_price,
                    "new_list_price": product.list_price,
                    "old_standard_price": old_standard_price,
                    "new_standard_price": product.standard_price,
                }
            )
        if history_vals:
            self.env["resonnocare.product.price.history"].sudo().create(history_vals)
        return res
