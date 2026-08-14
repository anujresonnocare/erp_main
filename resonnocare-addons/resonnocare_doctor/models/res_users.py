from odoo import fields, models
from odoo.exceptions import AccessError


class ResUsers(models.Model):
    _inherit = "res.users"

    external_doctor_profile_id = fields.Many2one(
        "resonnocare.doctor.profile",
        string="External Doctor Profile",
    )

    @property
    def SELF_READABLE_FIELDS(self):
        # Login flow reads these on the current user record.
        # Keep them self-readable so external doctors can authenticate
        # without requiring broad res.users record access.
        return super().SELF_READABLE_FIELDS + ["login_date", "company_id", "company_ids"]

    def _register_hook(self):
        result = super()._register_hook()
        # Ensure own user record is always visible to itself.
        # Some environments hit auth crashes when the default user rule
        # does not resolve properly for non-standard internal roles.
        base_user_rule = self.env.ref("base.res_users_rule", raise_if_not_found=False)
        if base_user_rule:
            expected = "['|', ('id', '=', user.id), '|', ('share', '=', False), ('company_ids', 'in', company_ids)]"
            if base_user_rule.domain_force != expected:
                base_user_rule.sudo().write({"domain_force": expected})
        return result

    def check_access(self, operation: str) -> None:
        try:
            return super().check_access(operation)
        except AccessError:
            if (
                operation == "read"
                and self
                and self.env.user.has_group("resonnocare_base.group_external_doctor")
                and set(self.ids) == {self.env.uid}
            ):
                return None
            raise

    def check_access_rule(self, operation):
        try:
            return super().check_access_rule(operation)
        except AccessError:
            if (
                operation == "read"
                and self
                and self.env.user.has_group("resonnocare_base.group_external_doctor")
                and set(self.ids) == {self.env.uid}
            ):
                return None
            raise
