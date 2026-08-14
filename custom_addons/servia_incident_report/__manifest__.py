# -*- coding: utf-8 -*-
{
    'name': 'Servia HSE Incident Report | Accident, Near-Miss & Safety Report',
    'version': '18.0.1.2.0',
    'category': 'Human Resources',
    'summary': 'HSE incident report: log accidents, near-misses, injuries and safety observations with severity, root cause and corrective action. Simple health & safety incident and accident register.',
    'description': """
Servia HSE Incident Report
==========================
A simple, clean health, safety and environment incident log.

* Record every incident: title, date, location and severity
* Capture description and action taken
* One-click Investigate / Close / Reopen workflow
* Filter by severity, reporter or status; group by severity or status
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
        'views/incident_report_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
