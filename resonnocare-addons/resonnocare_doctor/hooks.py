from odoo import SUPERUSER_ID, api


def post_init_hook(env):
    if not hasattr(env, "cr"):
        env = api.Environment(env, SUPERUSER_ID, {})
    legacy_xmlids = [
        "resonnocare_frontdesk.view_resonnocare_doctor_profile_tree",
        "resonnocare_frontdesk.view_resonnocare_doctor_profile_form",
        "resonnocare_frontdesk.action_resonnocare_doctor_profiles",
        "resonnocare_frontdesk.action_resonnocare_my_doctor_profile",
        "resonnocare_frontdesk.action_resonnocare_doctor_my_patients",
        "resonnocare_frontdesk.action_resonnocare_doctor_my_sales",
        "resonnocare_frontdesk.menu_external_doctor_root",
        "resonnocare_frontdesk.menu_external_doctor_profiles",
        "resonnocare_frontdesk.menu_external_doctor_my_profile",
        "resonnocare_frontdesk.menu_external_doctor_my_patients",
        "resonnocare_frontdesk.menu_external_doctor_my_sales",
        "resonnocare_frontdesk.doctor_profile_rule_external_doctor",
        "resonnocare_frontdesk.doctor_profile_rule_front_desk",
        "resonnocare_frontdesk.doctor_profile_rule_front_desk_read_all_v2",
        "resonnocare_frontdesk.patient_rule_external_doctor",
        "resonnocare_frontdesk.sale_order_rule_external_doctor",
    ]
    for xmlid in legacy_xmlids:
        rec = env.ref(xmlid, raise_if_not_found=False)
        if rec:
            rec.sudo().unlink()

    # No group migration needed; module reuses resonnocare_base.group_external_doctor.
