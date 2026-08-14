# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    supply_clinic_id = fields.Many2one(
        "resonnocare.clinic",
        string="Clinic",
        related="picking_id.supply_clinic_id",
        readonly=True,
        store=True,
    )
    supply_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Warehouse",
        related="picking_id.supply_warehouse_id",
        readonly=True,
        store=True,
    )
    ho_available_qty = fields.Float(
        string="HO Available Qty",
        compute="_compute_supply_planning_metrics",
        digits="Product Unit of Measure",
        store=False,
    )
    shortfall_qty = fields.Float(
        string="Shortfall Qty",
        compute="_compute_supply_planning_metrics",
        digits="Product Unit of Measure",
        store=False,
    )
    supply_readiness = fields.Selection(
        [
            ("ready", "Ready from HO Stock"),
            ("need_purchase", "Need Purchase"),
        ],
        string="Readiness",
        compute="_compute_supply_planning_metrics",
        store=False,
    )

    @api.depends("product_id", "product_uom_qty", "location_id", "state")
    def _compute_supply_planning_metrics(self):
        quant_model = self.env["stock.quant"].sudo()
        for move in self:
            move.ho_available_qty = 0.0
            move.shortfall_qty = 0.0
            move.supply_readiness = False

            if (
                move.state in ("done", "cancel")
                or not move.product_id
                or not move.location_id
                or not move.picking_id
                 or move.picking_id.picking_type_code != "internal"
                or not move.picking_id.is_clinic_supply
            ):
                continue

            available = quant_model._get_available_quantity(
                move.product_id, move.location_id, strict=False
            )
            required = move.product_uom_qty or 0.0
            shortfall = max(required - available, 0.0)
            move.ho_available_qty = available
            move.shortfall_qty = shortfall
            move.supply_readiness = "ready" if shortfall <= 0 else "need_purchase"
