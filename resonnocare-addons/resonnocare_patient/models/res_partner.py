# -*- coding: utf-8 -*-

from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools import email_normalize


class ResPartner(models.Model):
    _inherit = "res.partner"

    def action_generate_portal_signup_link(self):
        self.ensure_one()
        if not self.is_patient:
            raise UserError(_("Portal link can be generated only for patients."))
        if not self.email:
            raise UserError(_("Patient email is required to generate a portal link."))

        login = email_normalize(self.email)
        if not login:
            raise UserError(_("Please enter a valid patient email address."))

        group_portal = self.env.ref("base.group_portal")
        group_public = self.env.ref("base.group_public")
        group_patient = self.env.ref("resonnocare_base.group_patient")
        users_model = self.env["res.users"].sudo().with_context(active_test=False)

        user = self.user_ids[:1].sudo()
        if not user:
            existing_user = users_model.search([("login", "=", login)], limit=1)
            if existing_user and existing_user.partner_id != self:
                raise UserError(
                    _(
                        "The email '%(email)s' is already used by another user. "
                        "Use a unique email for this patient."
                    )
                    % {"email": login}
                )
            if existing_user:
                user = existing_user
            else:
                user = users_model.with_context(no_reset_password=True)._create_user_from_template(
                    {
                        "email": login,
                        "login": login,
                        "partner_id": self.id,
                        "company_id": self.env.company.id,
                        "company_ids": [(6, 0, self.env.company.ids)],
                    }
                )

        user.write(
            {
                "active": True,
                "groups_id": [
                    (4, group_portal.id),
                    (3, group_public.id),
                    (4, group_patient.id),
                ],
            }
        )

        partner = self.sudo()
        partner.signup_prepare(signup_type="signup")
        signup_url = partner.with_context(
            signup_force_type_in_url="signup"
        )._get_signup_url_for_action()[partner.id]

        return {
            "type": "ir.actions.act_window",
            "name": _("Patient Portal Signup Link"),
            "res_model": "resonnocare.patient.portal.link.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_partner_id": self.id,
                "default_portal_signup_url": signup_url,
            },
        }
