{
    'name': 'GST State Codes India',
    'version': '18.0.1.0.0',
    'category': 'Localization/India',
    'summary': 'Add Indian GST state codes, GSTIN and state headquarters to states',
    'description': '''
GST State Codes India
=====================

Adds GST state code information to Odoo Indian states and provides a dedicated
configuration menu to review/update GST state information.

Fields added to res.country.state:
- GST State Code
- GSTIN
- State HQ / Registration Address
- GST State Code Name
''',
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_country_state_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
}
