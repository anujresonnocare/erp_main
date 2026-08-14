# -*- coding: utf-8 -*-
{
    "name": "Resonnocare Patient Portal",
    "version": "18.0.1.0.0",
    "category": "Resonnocare",
    "summary": "Patient portal for profile and appointments",
    "author": "Resonnocare",
    "license": "LGPL-3",
    "depends": [
        "portal",
        "website",
        "sale",
        "account",
        "resonnocare_frontdesk",
        "resonnocare_appointment",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/portal_cleanup.xml",
        "views/portal_templates.xml",
        "views/patient_portal_link_wizard_views.xml",
        "views/res_partner_patient_form_inherit.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
