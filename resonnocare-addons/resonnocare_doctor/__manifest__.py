{
    "name": "Resonnocare Doctor",
    "version": "18.0.1.0.0",
    "category": "Resonnocare",
    "summary": "External doctor profiles, mapping, and commissions",
    "depends": [
        "resonnocare_base",
        "resonnocare_frontdesk",
        "resonnocare_appointment",
        "sale",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/sale_order_views.xml",
        "views/res_partner_patient_form_views.xml",
        "views/doctor_profile_views.xml",
        "views/patient_registration_wizard_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "resonnocare_doctor/static/src/scss/doctor_profile.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "post_init_hook": "post_init_hook",
    "license": "LGPL-3",
}
