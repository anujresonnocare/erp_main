# -*- coding: utf-8 -*-

{
    'name': 'Daily Prescription Report',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Daily Prescription Report Wizard with YTD, MTD, WTD, Yesterday',
    'description': """
        Daily Prescription Report Wizard
        =================================
        Generate daily prescription reports for device sales with:
        - YTD (Indian Financial Year - April 1 to date)
        - MTD (Month to Date)
        - WTD (Week to Date - Monday to date)
        - Yesterday
        
        Each sheet includes:
        - Clinic Name
        - Audiologist
        - Area Manager
        - Region
        - MRP
        - Discount
        - Net Prescription Value
        - Totals by Area Manager and Region
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'sale',
        'stock',
        'hr',
        'resonnocare_clinic',  # Change this to your actual module name
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/daily_prescription_report_wizard_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}