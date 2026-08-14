from odoo import models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    ho_warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="HO Warehouse",
        readonly=True,
    )

    ho_hearing_aid_sale_location_id = fields.Many2one(
        "stock.location",
        string="HO Saleable Hearing Aid Location",
        readonly=True,
    )

    ho_demo_hearing_aid_location_id = fields.Many2one(
        "stock.location",
        string="HO Demo Hearing Aid & Charger Location",
        readonly=True,
    )

    ho_saleable_accessories_location_id = fields.Many2one(
        "stock.location",
        string="HO Saleable Accessories Location",
        readonly=True,
    )

    ho_repair_service_location_id = fields.Many2one(
        "stock.location",
        string="HO Repair & Service Location",
        readonly=True,
    )

    ho_equipment_location_id = fields.Many2one(
        "stock.location",
        string="HO Equipment Location",
        readonly=True,
    )

    ho_consumable_location_id = fields.Many2one(
        "stock.location",
        string="HO Consumable Location",
        readonly=True,
    )

    ho_rtv_location_id = fields.Many2one(
        "stock.location",
        string="HO Return to Vendor (RTV) Location",
        readonly=True,
    )

    def _get_inventory_location_defs(self):
        return [
            ("ho_hearing_aid_sale_location_id", "Saleable Hearing Aid"),
            ("ho_demo_hearing_aid_location_id", "Demo Hearing Aid & Charger"),
            ("ho_saleable_accessories_location_id", "Saleable Accessories"),
            ("ho_repair_service_location_id", "Repair & Service"),
            ("ho_equipment_location_id", "Equipment"),
            ("ho_consumable_location_id", "Consumable"),
            ("ho_rtv_location_id", "Return to Vendor (RTV)"),
        ]

    def _get_unique_ho_warehouse_code(self, company, base_code="HO"):
        StockWarehouse = self.env["stock.warehouse"].sudo()
        code = base_code
        exists = StockWarehouse.search_count(
            [("code", "=", code), ("company_id", "=", company.id)]
        )
        if not exists:
            return code
        alt_code = f"H{company.id}"[:5]
        if alt_code and not StockWarehouse.search_count(
            [("code", "=", alt_code), ("company_id", "=", company.id)]
        ):
            return alt_code
        return f"HO{company.id}"[:5]

    def _ensure_ho_warehouse_and_locations(self):
        StockWarehouse = self.env["stock.warehouse"].sudo()
        StockLocation = self.env["stock.location"].sudo()

        for company in self:
            warehouse = company.ho_warehouse_id
            if not warehouse:
                warehouse = StockWarehouse.search(
                    [
                        ("company_id", "=", company.id),
                        ("code", "=", "HO"),
                    ],
                    limit=1,
                )

            if not warehouse:
                warehouse = StockWarehouse.search(
                    [
                        ("company_id", "=", company.id),
                        ("name", "ilike", "HO"),
                    ],
                    limit=1,
                )

            if not warehouse:
                warehouse = StockWarehouse.create(
                    {
                        "name": f"{company.name} HO",
                        "code": self._get_unique_ho_warehouse_code(company),
                        "company_id": company.id,
                    }
                )

            if not warehouse.lot_stock_id:
                warehouse = warehouse.with_company(company.id)
                warehouse._create_or_update_locations()
                warehouse.invalidate_recordset(["lot_stock_id"])

            parent = warehouse.lot_stock_id
            updates = {"ho_warehouse_id": warehouse.id}

            if parent:
                for field_name, location_name in company._get_inventory_location_defs():
                    current = company[field_name]
                    if current and current.location_id == parent:
                        continue

                    existing = StockLocation.search(
                        [
                            ("location_id", "=", parent.id),
                            ("name", "=", location_name),
                            ("usage", "=", "internal"),
                        ],
                        limit=1,
                    )

                    if not existing:
                        existing = StockLocation.create(
                            {
                                "name": location_name,
                                "location_id": parent.id,
                                "usage": "internal",
                                "company_id": warehouse.company_id.id,
                            }
                        )

                    updates[field_name] = existing.id

            company.sudo().write(updates)

    def action_backfill_ho_inventory_locations(self):
        self._ensure_ho_warehouse_and_locations()
