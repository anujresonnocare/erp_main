{
    'name': 'CRM Lead Notification Bell',
    'version': '18.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Adds notification bell for CRM lead stage changes',
    'description': """
        This module adds a notification bell icon in the top right corner
        that shows notifications when CRM leads change stages.
    """,
    'author': 'Your Company',
    'depends': ['crm', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/crm_lead_views.xml',
        'views/res_users_views.xml',
        'data/notification_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'crm_lead_notification_bell/static/src/css/notification_bell.css',
            'crm_lead_notification_bell/static/src/js/notification_bell.js',
            'crm_lead_notification_bell/static/src/xml/notification_bell.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}