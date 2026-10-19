{
    'name': 'Cash Deposit Reconciliation',
    'version': '18.0.1.0.0',
    'summary': 'Track cash entries, deposit to bank with slip, finance verifies',
    'category': 'Accounting',
    'author': 'Your Company',
    'license': 'LGPL-3',
    'depends': ['base', 'account'],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'security/security_rules.xml',
        'views/deposit_wizard_views.xml',   # ← MOVED UP: defines action_deposit_wizard
        'views/cash_entry_views.xml',       # ← now the reference resolves
        'views/bank_deposit_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
}