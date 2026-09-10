# -*- coding: utf-8 -*-

{
    "name": "Resonnocare Report: CDT Journey",
    "version": "18.0.1.0.0",
    "category": "Resonnocare",
    "summary": "HQ administration & dashboards for Resonnocare",

    "description": """
        Resonnocare Admin
        =================

        HQ administration, dashboards and journey management
        for Resonnocare.
    """,

    "author": "Resonnocare",
    "license": "LGPL-3",

    "depends": [
        "base", "resonnocare_clinic", "resonnocare_base"
    ],

    "data": [
        "security/ir.model.access.csv",
        "views/views.xml",
        "views/templates.xml",
    ],

    "installable": True,
    "application": True,
}