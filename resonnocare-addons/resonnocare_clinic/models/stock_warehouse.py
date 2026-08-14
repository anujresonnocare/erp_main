from odoo import models


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    def action_create_resonnocare_locations(self):
        StockLocation = self.env["stock.location"].sudo()

        for warehouse in self:
            if not warehouse.lot_stock_id:
                warehouse = warehouse.with_company(warehouse.company_id.id)
                warehouse._create_or_update_locations()
                warehouse.invalidate_recordset(["lot_stock_id"])

            parent = warehouse.lot_stock_id or warehouse.view_location_id
            if not parent:
                continue

            location_defs = [
                ("Saleable Hearing Aid", "ho_hearing_aid_sale_location_id"),
                ("Demo Hearing Aid & Charger", "ho_demo_hearing_aid_location_id"),
                ("Saleable Accessories", "ho_saleable_accessories_location_id"),
                ("Repair & Service", "ho_repair_service_location_id"),
                ("Equipment", "ho_equipment_location_id"),
                ("Consumable", "ho_consumable_location_id"),
                ("Return to Vendor (RTV)", "ho_rtv_location_id"),
            ]

            updates = {}
            for location_name, company_field in location_defs:
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
                updates[company_field] = existing.id

            company = warehouse.company_id.sudo()
            if not company.ho_warehouse_id or company.ho_warehouse_id.id == warehouse.id:
                company.write({"ho_warehouse_id": warehouse.id, **updates})
