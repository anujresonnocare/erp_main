# -*- coding: utf-8 -*-
{
    "name": "Resonnocare Inventory",
    "version": "18.0.1.0.0",
    "category": "Resonnocare",
    "summary": "Device Management (Inventory Listing)",
    "description": """
Resonnocare Inventory – Phase 1

• Device listing per clinic
• Availability tracking
• Appointment device selection support

No stock, no vendors, no pricing, no billing.
""",
    "author": "Resonnocare",
    "license": "LGPL-3",

    "depends": [
        "base",
        "stock",
        "product_expiry",
        "resonnocare_base",
        "resonnocare_clinic",
    ],

    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/stn_sequence.xml",
        "data/grn_sequence.xml",
        "views/product_price_history_views.xml",
        "views/product_template_views.xml",
        "views/stock_lot_views.xml",
        "views/stock_move_supply_planning_views.xml",
        "views/stock_picking_views.xml",
        "views/supply_docket_upload_wizard_views.xml",
        "views/vendor_registration.xml",
        "views/menu.xml",
    ],

    "installable": True,
    "application": False,
    "auto_install": False,
}
