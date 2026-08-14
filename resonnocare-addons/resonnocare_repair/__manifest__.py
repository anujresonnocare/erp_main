{
    "name": "Resonnocare Repair",
    "version": "18.0.1.0.0",
    "category": "Resonnocare",
    "summary": "Repair and Service management for Resonnocare",
    "description": """
        Tracks custom Hearing Aid & Accessories Repair process map:
        - Corporate vs Revenue Sharing billing modes
        - Warranty details auto-populating from Serial Numbers (stock.lot)
        - Handling and Repair charges tracking
        - Lab dispatch and tracking
        - Repair GRN integration
        - Handover and invoicing
    """,
    "depends": [
        "base",
        "sale",
        "purchase",
        "stock",
        "account",
        "resonnocare_base",
        "resonnocare_clinic",
        "resonnocare_inventory",
        "resonnocare_master",
        "resonnocare_frontdesk",
        "resonnocare_appointment"
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/repair_sequence.xml",
        "data/maintenance_sequence.xml",
        "views/report_repair_contract.xml",
        "views/repair_contract_views.xml",
        "views/device_maintenance_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
