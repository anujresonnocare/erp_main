{
    "name": "Resonnocare Admin",
    "version": "18.0.1.0.0",
    "category": "Resonnocare",
    "summary": "HQ administration & dashboards for Resonnocare",
    "depends": [
        "base",
        "web",
        "resonnocare_base",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/dashboard_data.xml",
        "views/admin_placeholder_action.xml",
        "views/hq_dashboard_view.xml",
        "views/hq_dashboard_action.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": True,
    'license': 'LGPL-3',
}
