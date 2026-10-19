{
    'name': 'Resonnocare Cash Management',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Cash denomination validation for Cash journals',
    'depends': ['account'],
    'data': [
        # Put the views first so Odoo knows the models exist, then the security
        'views/account_payment_views.xml',
        'views/account_payment_register_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}