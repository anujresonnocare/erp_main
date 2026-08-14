# -*- coding: utf-8 -*-
{
    'name': 'Servia Safety Inspection Checklist',
    'version': '18.0.1.0.0',
    'category': 'Services',
    'summary': 'Log health & safety inspections with area, inspector, date, result and findings. Keep a clear HSE audit trail.',
    'description': """
Servia Safety Inspection Checklist
==================================
Record workplace safety inspections.

* Record each inspection: area, inspector and date.
* Capture the result (pass/fail), risk level and findings.
* Confirm records; filter and group by area or result.
* Simple HSE inspection log for any workplace.
* Works on Odoo Community, Enterprise and Odoo.sh, versions 12 to 19

Installation and customization by Servia - see the description page.
""",
    'author': 'Servia',
    'website': 'https://servia.ae',
    'license': 'LGPL-3',
    'price': 0.0,
    'currency': 'USD',
    'support': 'support@servia.ae',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/servia_safety_inspection_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
