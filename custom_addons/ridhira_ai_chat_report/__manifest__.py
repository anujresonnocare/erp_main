# -*- coding: utf-8 -*-
{
    'name': 'AI Chat-to-Report & Dashboard Assistant',
    'version': '18.0.1.0.0',
    'category': 'Productivity/Dashboard',
    'summary': 'The High-Ticket Modernizer: Natural Language query bar to generate reports, charts, and pivot tables using AI.',
    'description': """
        AI Chat-to-Report & Dashboard Assistant
        =======================================
        Unlock your Odoo data with plain English queries.
        This module allows users to generate complex charts and reports instantly 
        using LLMs (OpenAI, Gemini, Anthropic) and pin them to their dashboards.
    """,
    'author': 'Ridhira Technologies , Pune , India',
    'website': 'https://ridhira.desigoogly.com',
    'images': ['static/description/banner.png'],
    'depends': ['base', 'web', 'board'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/ai_report_actions.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ridhira_ai_chat_report/static/src/css/ai_report.scss',
            'ridhira_ai_chat_report/static/src/components/ai_query_bar/ai_query_bar.xml',
            'ridhira_ai_chat_report/static/src/components/ai_query_bar/ai_query_bar.js',
        ],
    },
    'license': 'OPL-1',
    'installable': True,
    'application': True,
    'auto_install': False,
}
