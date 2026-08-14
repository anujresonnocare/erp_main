# -*- coding: utf-8 -*-

from odoo import fields, models


class PatientPortalLinkWizard(models.TransientModel):
    _name = "resonnocare.patient.portal.link.wizard"
    _description = "Patient Portal Link Wizard"

    partner_id = fields.Many2one("res.partner", string="Patient", readonly=True)
    portal_signup_url = fields.Char(string="Portal Signup Link", readonly=True)

    def action_send_email(self):
        self.ensure_one()
        partner = self.partner_id.sudo()
        if not partner.email:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Missing Email",
                    "message": "Patient email is not set.",
                    "type": "warning",
                    "sticky": False,
                },
            }

        mail_values = {
            "subject": "Resonnocare Patient Portal Access",
            "email_to": partner.email,
            "body_html": (
                "<p>Dear %s,</p>"
                "<p>Please use the below link to set your password and access your Resonnocare patient portal:</p>"
                "<p><a href='%s'>%s</a></p>"
                "<p>Regards,<br/>Resonnocare Team</p>"
            )
            % (partner.name or "Patient", self.portal_signup_url, self.portal_signup_url),
        }
        self.env["mail.mail"].sudo().create(mail_values).send()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Email Sent",
                "message": f"Signup link sent to {partner.email}.",
                "type": "success",
                "sticky": False,
            },
        }
