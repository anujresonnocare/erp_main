{
    'name': 'Resonnocare Cash Management',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Cash denomination validation for Cash journals',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_payment_views.xml',
        'views/account_payment_register_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}