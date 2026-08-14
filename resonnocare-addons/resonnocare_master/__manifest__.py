# -*- coding: utf-8 -*-
{
    "name": "Resonnocare Masters",
    "version": "1.0",
    "summary": "Global master data for Resonnocare ERP",
    "description": """
Centralised master data management for Resonnocare.
Includes:
- Call Dispositions
- Appointment Types
- Appointment Outcomes

Editable only by Super Admin.
Read-only for all operational roles.
    """,
    "author": "Resonnocare",
    "depends": [
        "base",
        "resonnocare_base",
        "resonnocare_admin",
    ],
    "data": [
        # Security
        "security/security.xml",
        "security/ir.model.access.csv",
        # Views (actions FIRST)
        "views/crm_disposition_views.xml",
        "views/appointment_type_views.xml",
        "views/appointment_outcome_views.xml",
        "views/appointment_diag_items_views.xml",
        "views/discount_grid_views.xml",
        "views/gst_rate_matrix_views.xml",
        # Menus (after actions exist)
        "views/menu.xml",
        # Seed data
        "data/crm_disposition_data.xml",
        "data/appointment_type_sequence.xml",
        "data/appointment_type_data.xml",
        "data/appointment_outcome_data.xml",
        "data/discount_grid_data.xml",
        "data/gst_rate_matrix_data.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
