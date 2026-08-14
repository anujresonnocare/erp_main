# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
{
    "name": "Employee Medical Information",
    "version": "18.0.0.0",
    "category": "Human Resources",
    "summary": "Employee Health Mediclaim HR Medical Examination Policy Worker Medical History Hr Employee Medical System Employee Health Insurance Office Staff Physical Examination Employee Medical Test Employee Physical Health Check-up Hr Medical Information",
    "description": """

        Employee Medical Information Odoo App helps users to managing employee medical examination and send time to time reminder for medical examination. User have options to set different notification type and based on that employee will get an email notification about medical examination dates.

    """,
    "author": "BROWSEINFO",
    "website" : "https://www.browseinfo.com/demo-request?app=bi_employee_medical_examination_management&version=18&edition=Community",
    "depends" : ['hr'],
    "external_dependencies": {
            'python': ['pandas'],
        },
    "data": [
            "security/ir.model.access.csv",
            "views/hr_employee_medical_examination_view.xml",
            "views/hr_employee_views.xml",

        ],
    'license':'OPL-1',
    'installable': True,
    'auto_install': False,
    'live_test_url':'https://www.browseinfo.com/demo-request?app=bi_employee_medical_examination_management&version=18&edition=Community',
    "images":['static/description/Employee-Medical-Information-Banner.gif'],
}

