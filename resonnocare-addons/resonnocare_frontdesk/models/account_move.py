from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = "account.move"

    clinic_id = fields.Many2one(
        "resonnocare.clinic",
        string="Clinic",
        index=True,
        readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("clinic_id"):
                partner_id = vals.get("partner_id")
                if partner_id:
                    partner = self.env["res.partner"].browse(partner_id)
                    if partner.is_patient and partner.clinic_id:
                        vals["clinic_id"] = partner.clinic_id.id

            if not vals.get("clinic_id") and vals.get("move_type") in ("out_invoice", "out_refund"):
                user_clinic = self.env.user.employee_id.clinic_id
                if user_clinic:
                    vals["clinic_id"] = user_clinic.id

        return super().create(vals_list)
