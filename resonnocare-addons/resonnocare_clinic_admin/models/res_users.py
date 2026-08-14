from odoo import models
from odoo.exceptions import AccessDenied


class ResUsers(models.Model):
    _inherit = "res.users"

    def _check_credentials(self, password, user_agent_env):
        """Validate clinic status for clinic admins after standard auth check."""
        result = super()._check_credentials(password, user_agent_env)

        # Portal password change can call this method on an empty recordset.
        users = self if self else self.env.user
        for user in users:
            if user.has_group("resonnocare_base.group_clinic_admin"):
                clinic = user.clinic_id
                if clinic and clinic.clinic_status != "active":
                    raise AccessDenied(
                        f"Your clinic ({clinic.name}) is not active.\n"
                        f"Status: {dict(clinic._fields['clinic_status'].selection).get(clinic.clinic_status)}\n\n"
                        "Please contact Resonnocare HQ."
                    )

        return result
