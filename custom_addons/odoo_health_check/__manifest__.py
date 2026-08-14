{
    "name": "Odoo Health Check",
    "version": "18.0.1.12.4",
    "summary": "Cron execution history, disk monitoring, monthly PostgreSQL growth reports",
    "description": """
Odoo Health Check
=================

Daily health check for your Odoo 18 Enterprise self-hosted installation.

Features
--------
* Cron execution history with duration and error traceback
* Email alert on every failed cron run
* Disk space monitoring on OS root and Odoo filestore mount
* Monthly PostgreSQL growth report (top tables by size, row count)

Localised UI and email alerts in 8 languages: English, Russian (ru),
Ukrainian (uk), German (de), Spanish (es), Romanian (ro), Polish (pl),
Arabic (ar). Translations apply automatically based on the user's
language preference.

Targeted at Odoo 18 Enterprise. Community may work but is not tested.
""",
    "author": "Rteam",
    "website": "https://rteam.agency",
    "license": "LGPL-3",
    "category": "Administration",
    "depends": ["base", "mail"],
    "images": ["static/description/banner.png"],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_template_data.xml",
        "data/ir_cron_data.xml",
        "data/health_check_dashboard_data.xml",
        "views/ir_cron_history_views.xml",
        "views/health_check_result_views.xml",
        "views/health_check_dashboard_views.xml",
        "views/res_config_settings_views.xml",
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_web_dark": [
            "odoo_health_check/static/src/scss/dark_mode_icon.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
