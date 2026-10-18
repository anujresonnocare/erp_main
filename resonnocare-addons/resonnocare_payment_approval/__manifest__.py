{
    'name': 'Resonnocare Payment Approval',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Require finance approval for payments using specific journals',
    'depends': ['account', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_journal_views.xml',
        'views/payment_approval_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}