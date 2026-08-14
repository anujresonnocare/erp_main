from odoo import fields, models
from odoo.exceptions import UserError


class ResonnocareAppointmentCompleteWizard(models.TransientModel):
    _name = "resonnocare.appointment.complete.wizard"
    _description = "Complete Appointment Wizard"

    appointment_id = fields.Many2one(
        "resonnocare.appointment",
        string="Appointment",
        required=True,
        readonly=True,
    )
    outcome_ids = fields.Many2many(
        "resonnocare.appointment.outcome",
        "resonnocare_appointment_complete_wizard_outcome_rel",
        "wizard_id",
        "outcome_id",
        string="Appointment Outcomes",
        required=True,
    )

    def action_confirm_complete(self):
        self.ensure_one()
        appointment = self.appointment_id
        if not appointment:
            raise UserError("Appointment not found.")
        if appointment.status != "in_consultation":
            raise UserError("Only appointments in consultation can be completed.")
        if appointment.parent_appointment_id and (appointment.balance_due or 0.0) > 0:
            raise UserError(
                "Fitting appointment cannot be completed while balance due is greater than 0."
            )
        if not self.outcome_ids:
            raise UserError("Please select at least one appointment outcome.")

        appointment.write(
            {
                "appointment_outcome_ids": [(6, 0, self.outcome_ids.ids)],
                "status": "completed",
            }
        )
        return {"type": "ir.actions.act_window_close"}
