# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import api, fields, models


class ResonnocareSupplyPurchasePlan(models.TransientModel):
    _name = "resonnocare.supply.purchase.plan"
    _description = "SCM Supply Purchase Plan"
    _order = "qty_to_purchase desc, total_required_qty desc, id desc"
    _rec_name = "product_id"

    product_id = fields.Many2one("product.product", string="Product", required=True, readonly=True)
    company_id = fields.Many2one("res.company", string="Company", required=True, readonly=True)
    uom_id = fields.Many2one("uom.uom", string="UoM", readonly=True)
    pending_order_count = fields.Integer(string="Pending Orders", readonly=True)
    clinic_count = fields.Integer(string="Clinics", readonly=True)
    total_required_qty = fields.Float(string="Total Required Qty", readonly=True)
    ho_available_qty = fields.Float(string="HO Available Qty", readonly=True)
    qty_to_purchase = fields.Float(string="Qty to Purchase", readonly=True)
    generated_on = fields.Datetime(string="Generated On", readonly=True)

    @api.model
    def _rebuild_purchase_plan(self):
        plan_model = self
        plan_model.search([]).unlink()

        move_domain = [
            ("picking_id.picking_type_code", "=", "internal"),
            ("picking_id.is_clinic_supply", "=", True),
            ("state", "not in", ("done", "cancel")),
            ("product_id", "!=", False),
            ("product_uom_qty", ">", 0),
        ]
        moves = self.env["stock.move"].sudo().search(move_domain)
        if not moves:
            return

        grouped = defaultdict(
            lambda: {"required": 0.0, "pickings": set(), "clinics": set(), "uom_id": False}
        )
        for mv in moves:
            key = (mv.company_id.id, mv.product_id.id)
            grouped[key]["required"] += mv.product_uom_qty or 0.0
            grouped[key]["pickings"].add(mv.picking_id.id)
            if mv.picking_id.supply_clinic_id:
                grouped[key]["clinics"].add(mv.picking_id.supply_clinic_id.id)
            grouped[key]["uom_id"] = mv.product_uom.id

        now_dt = fields.Datetime.now()
        vals_list = []
        quant_model = self.env["stock.quant"].sudo()
        for (company_id, product_id), stats in grouped.items():
            company = self.env["res.company"].sudo().browse(company_id)
            product = self.env["product.product"].sudo().browse(product_id)
            ho_location = company.ho_hearing_aid_sale_location_id or (
                company.ho_warehouse_id.lot_stock_id if company.ho_warehouse_id else False
            )
            available = (
                quant_model._get_available_quantity(product, ho_location, strict=False)
                if ho_location
                else 0.0
            )
            required = stats["required"]
            to_purchase = max(required - available, 0.0)
            vals_list.append(
                {
                    "product_id": product_id,
                    "company_id": company_id,
                    "uom_id": stats["uom_id"],
                    "pending_order_count": len(stats["pickings"]),
                    "clinic_count": len(stats["clinics"]),
                    "total_required_qty": required,
                    "ho_available_qty": available,
                    "qty_to_purchase": to_purchase,
                    "generated_on": now_dt,
                }
            )
        if vals_list:
            plan_model.create(vals_list)

    @api.model
    def action_open_purchase_plan(self):
        self._rebuild_purchase_plan()
        return {
            "type": "ir.actions.act_window",
            "name": "Purchase Plan (Bulk)",
            "res_model": "resonnocare.supply.purchase.plan",
            "view_mode": "list,pivot,graph",
            "domain": [],
            "context": {"create": False, "edit": False, "delete": False},
        }
