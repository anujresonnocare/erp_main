{
    "name": "Resonnocare Base",
    "version": "18.0.1.0.0",
    "category": "Resonnocare",
    "summary": "Core foundation for Resonnocare ERP",
    "depends": [
        "base",
        "contacts",
        "purchase"
        ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        'views/resonnocare_operations_menu.xml',
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    'license': 'LGPL-3',
}
