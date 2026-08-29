{
    'name': 'Custom Source Hierarchy',
    'version': '18.0.1.0.0',
    'category': 'Tools',
    'summary': 'Custom source with parent-child hierarchy',
    'description': """
        This module adds a custom source model with hierarchical parent-child relationships.
        Features:
        - Parent-child relationship support
        - Hierarchy view with drag-and-drop
        - Optimized for large datasets
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/custom_source_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}