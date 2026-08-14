# -*- coding: utf-8 -*-
{
    "name": "Resonnocare CRM",
    "version": "1.0",
    "summary": "Extended CRM for Resonnocare",
    "description": """
        Extends Odoo CRM specifically for Resonnocare requirements:
        - Call Dispositions
        - Visit Intent Tracking
        - Automated Follow-ups
    """,
    "author": "Resonnocare",
    "depends": [
        "crm",
        "sale_crm",
        "crm_iap_enrich",
        "mail",
        "contacts",
        "resonnocare_base",
        "resonnocare_master",
        "resonnocare_appointment",
    ],
    "data": [
        "data/crm_call_log_sequence.xml",
        "data/crm_churn_campaign_sequence.xml",
        "data/crm_settings.xml",
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/crm_lead_views.xml",
        "views/crm_churn_campaign_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
