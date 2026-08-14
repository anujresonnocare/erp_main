from odoo import models, fields, api


class ResonnocareClinicDiagnostic(models.Model):
    _name = "resonnocare.clinic.diagnostic"
    _description = "Clinic Diagnostic Pricing"
    _rec_name = "diagnostic_item_id"

    clinic_id = fields.Many2one(
        "resonnocare.clinic",
        string="Clinic",
        required=True,
        ondelete="cascade",
        index=True,
    )

    diagnostic_item_id = fields.Many2one(
        "resonnocare.diagnostic.item",
        string="Diagnostic Item",
        required=True,
        index=True,
    )

    mrp = fields.Float(string="MRP", required=True)

    price_history_ids = fields.One2many(
        "resonnocare.clinic.diagnostic.price.history",
        "clinic_diagnostic_id",
        string="Price History",
        readonly=True,
    )

    _sql_constraints = [
        (
            "uniq_clinic_diagnostic_item",
            "unique(clinic_id, diagnostic_item_id)",
            "Diagnostic pricing already exists for this clinic and diagnostic item.",
        )
    ]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        history_vals = []
        for rec in records:
            history_vals.append(
                {
                    "clinic_diagnostic_id": rec.id,
                    "old_mrp": rec.mrp,
                    "new_mrp": rec.mrp,
                    "change_note": "Initial price",
                }
            )
        if history_vals:
            self.env["resonnocare.clinic.diagnostic.price.history"].sudo().create(history_vals)
        return records

    def write(self, vals):
        track_mrp = "mrp" in vals
        if not track_mrp:
            return super().write(vals)

        old_mrp_by_id = {rec.id: rec.mrp for rec in self}
        res = super().write(vals)

        history_vals = []
        for rec in self:
            old_mrp = old_mrp_by_id.get(rec.id)
            if old_mrp is None:
                continue
            if old_mrp == rec.mrp:
                continue
            history_vals.append(
                {
                    "clinic_diagnostic_id": rec.id,
                    "old_mrp": old_mrp,
                    "new_mrp": rec.mrp,
                }
            )
        if history_vals:
            self.env["resonnocare.clinic.diagnostic.price.history"].sudo().create(history_vals)
        return res
