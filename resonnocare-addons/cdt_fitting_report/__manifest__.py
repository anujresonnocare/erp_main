# -*- coding: utf-8 -*-
{
    'name': 'CDT Fitting Report',
    'version': '1.0',
    'category': 'Reporting',
    'summary': 'Fitting Report for CDT Clinics',
    'description': """
        This module generates fitting reports based on appointments.
        It captures fitting data from appointments with fitting type and their linked sale orders.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'sale',
        'product',
        'resonnocare_clinic',  # Your clinic module
        'resonnocare_appointment',  # Your appointment module
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/cdt_fitting_report_wizard_view.xml',
        'views/menu_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}