# -*- coding: utf-8 -*-
{
    'name': 'Clinic Order Cancellation & Return',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Cancel appointments with sale order returns and credit notes',
    'description': """
        This module adds functionality to cancel appointments and automatically:
        - Cancel linked sale orders
        - Create return orders for delivered products
        - Generate credit notes for invoices
    """,
    'author': 'Your Company',
    'depends': ['sale', 'account', 'stock', 'resonnocare_appointment'],
    'data': [
        'security/ir.model.access.csv',
        'views/deposit_wizard_views.xml',   # ← move UP (defines action_deposit_wizard)
        'views/cash_entry_views.xml',       # ← can now reference it
        'views/bank_deposit_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
}