from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResonnocarePatientRegistrationWizard(models.TransientModel):
    _inherit = "resonnocare.patient.registration.wizard"

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
        self.referring_doctor = self.referring_doctor_id.name or False

    def action_register_patient(self):
        for wizard in self:
            if wizard.referral_source == "doctor" and not wizard.referring_doctor_id:
                raise UserError(
                    _(
                        "Please select Referring Doctor Profile for Doctor referral source."
                    )
                )
        action = super().action_register_patient()
        for wizard in self:
            if wizard.referring_doctor_id and wizard.phone:
                patient = self.env["res.partner"].search(
                    [
                        ("phone", "=", wizard.phone),
                        ("is_patient", "=", True),
                        ("company_id", "=", self.env.company.id),
                    ],
                    order="id desc",
                    limit=1,
                )
                if patient:
                    patient.write(
                        {
                            "referring_doctor_id": wizard.referring_doctor_id.id,
                            "referring_doctor": wizard.referring_doctor_id.name,
                        }
                    )
        return action
