{
    "name": "Resonnocare Clinic Admin",
    "version": "18.0.1.0.0",
    "category": "Resonnocare",
    "summary": "Clinic Admin operational UI for Resonnocare clinics",
    "description": """
    Clinic Admin interface for Resonnocare ERP.
    Provides operational dashboard and tools for clinic administrators.
    """,
    "depends": [
        "resonnocare_base",
        "resonnocare_clinic",
        "resonnocare_hr",
        "resonnocare_frontdesk",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/dashboard_view.xml",
        "views/staff_view.xml",
        "views/server_actions.xml",
        "views/clinic_profile_view.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": True,  # This makes the menu appear in top bar
    "auto_install": False,
    'license': 'LGPL-3',
}
