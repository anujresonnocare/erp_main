{
    "name": "Account Payment Matching",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "summary": "Payment Matching for Odoo Community",
    "author": "Anuj Chauhan",
    "license": "LGPL-3",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "views/account_payment_views.xml",
    ],
    "assets": {
        "web.assets_backend": []
    },
    "installable": True,
    "application": False,
}
