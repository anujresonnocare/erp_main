# -*- coding: utf-8 -*-

{
    "name": "Resonnocare Appointments",
    "version": "18.0.1.0.0",
    "category": "Resonnocare",
    "summary": "Core clinical appointment management for Resonnocare",
    "description": """
Resonnocare Appointments Module

- Central clinical appointment entity
- Appointments created by Front Desk
- Appointments consumed by Doctors
- Diagnostic Items supported (clinical services, not inventory)
- Strict status lifecycle with button-driven transitions
- CRM integration is intent-only (read-only reference)

Explicit exclusions:
- No billing
- No inventory
- No slot engine
- No automation
""",
    "author": "Resonnocare",
    "license": "LGPL-3",

    # IMPORTANT: dependency order matters
    "depends": [
        "base",
        "resonnocare_master",      # appointment types, outcomes, diagnostic items
        "resonnocare_frontdesk",   # appointment creation UI / wizards
        "resonnocare_clinic",
        "resonnocare_inventory",
        # "crm",  # add ONLY if you store crm.lead relation
    ],

    "data": [
        # Security
        "security/ir.model.access.csv",
        "security/security.xml",

        # Data
        "data/contract_sequence.xml",
        "data/ear_mould_form_sequence.xml",

        # Views
        "views/account_move_payment_views.xml",
        "views/account_move_views.xml",
        "views/appointment_complete_wizard_views.xml",
        # Audiometry results views must be loaded before appointment views
        "views/audiometry_result_views.xml",
        "views/appointment_views.xml",
        "views/ear_mould_form_views.xml",
        "views/product_template_views.xml",
        "views/appointment_menu.xml",
        "views/report_invoice.xml",
        "views/report_payment_receipt.xml",
        "views/report_contract.xml",
        "views/report_ear_mould_form.xml",
        
    ],

    "installable": True,
    "application": False,
    "auto_install": False,
}
