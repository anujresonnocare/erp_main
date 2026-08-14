from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    referring_doctor_id = fields.Many2one(
        "resonnocare.doctor.profile",
        string="Referring Doctor Profile",
        domain=[
            ("state", "=", "approved"),
            ("change_type", "=", "addition"),
            ("active", "=", True),
        ],
    )

    @api.onchange("referring_doctor_id")
    def _onchange_referring_doctor_id(self):
        for rec in self:
            rec.referring_doctor = rec.referring_doctor_id.name or False

    def _register_hook(self):
        result = super()._register_hook()
        # Keep external doctor partner rule aligned with the intended domain.
        # This also prevents delegated res.users access from being blocked
        # through partner_id during authentication.
        doctor_group = self.env.ref(
            "resonnocare_base.group_external_doctor", raise_if_not_found=False
        )
        expected_domain = (
            "["
            " '|',"
            " ('id', '=', user.partner_id.id),"
            " '&',"
            " ('is_patient', '=', True),"
            " ('referring_doctor_id', '=', user.external_doctor_profile_id.id)"
            "]"
        )
        if doctor_group:
            rules = (
                self.env["ir.rule"]
                .sudo()
                .search(
                    [
                        ("model_id.model", "=", "res.partner"),
                        ("groups", "in", doctor_group.id),
                        ("name", "=", "Patients: External Doctor Own Referrals"),
                    ]
                )
            )
            if rules:
                rules.write({"domain_force": expected_domain})
        return result
