from odoo import _, fields, models
from odoo.exceptions import AccessDenied


class ResUsers(models.Model):
    _inherit = "res.users"

    clinic_id = fields.Many2one(
        "resonnocare.clinic",
        string="Assigned Clinic",
        help="The clinic this user is assigned to for operational purposes",
    )

    def _get_operational_group_ids(self):
        xmlids = (
            "resonnocare_base.group_clinic_admin",
            "resonnocare_base.group_front_desk",
            "resonnocare_base.group_doctor",
            "resonnocare_base.group_resonnocare_internal",
        )
        group_ids = []
        for xmlid in xmlids:
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group:
                group_ids.append(group.id)
        return group_ids

    def _is_clinic_operational_user(self):
        self.ensure_one()
        operational_group_ids = set(self._get_operational_group_ids())
        if not operational_group_ids:
            return False
        return bool(operational_group_ids.intersection(set(self.sudo().groups_id.ids)))

    def _get_effective_clinic(self):
        self.ensure_one()
        user = self.sudo()
        return user.clinic_id or user.employee_id.clinic_id

    def _check_credentials(self, password, user_agent_env):
        result = super()._check_credentials(password, user_agent_env)

        for user in self:
            # Skip clinic validation for system/admin users
            if user.has_group("base.group_system"):
                continue
            
            if not user._is_clinic_operational_user():
                continue

            clinic = user._get_effective_clinic()
            if not clinic:
                raise AccessDenied(
                    _(
                        "Your account is not assigned to any clinic yet. Please contact HR/Admin."
                    )
                )

            if clinic.clinic_status != "active":
                status_label = dict(clinic._fields["clinic_status"].selection).get(
                    clinic.clinic_status, clinic.clinic_status
                )
                raise AccessDenied(
                    _(
                        "Your clinic (%(clinic)s) is not active yet. Current status: %(status)s. "
                        "Please contact Resonnocare HQ."
                    )
                    % {"clinic": clinic.name, "status": status_label}
                )

        return result
