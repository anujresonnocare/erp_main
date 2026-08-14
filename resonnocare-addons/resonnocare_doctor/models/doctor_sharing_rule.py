from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResonnocareDoctorSharingRule(models.Model):
    _name = "resonnocare.doctor.sharing.rule"
    _description = "Doctor Sharing Rule"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    doctor_id = fields.Many2one(
        "resonnocare.doctor.profile",
        required=True,
        ondelete="cascade",
        index=True,
    )
    apply_scope = fields.Selection(
        [("standard", "Standard Clinics"), ("different", "Different Sharing Clinics")],
        required=True,
        default="standard",
        index=True,
    )
    clinic_id = fields.Many2one("resonnocare.clinic", required=True, index=True)
    clinic_display_name = fields.Char(
        string="Clinic",
        compute="_compute_clinic_display_name",
    )
    rule_level = fields.Selection(
        [
            ("flat", "Flat Sharing"),
            ("mrp", "MRP Slab Sharing"),
            ("item", "Item Based Sharing"),
            ("source", "Source Based Sharing"),
        ],
        required=True,
        default="flat",
        index=True,
    )
    product_category = fields.Selection(
        [
            ("hearing_device", "Hearing Device"),
            ("diagnostic_services", "Diagnostic Services"),
            ("accessories_sale", "Accessories Sale"),
            ("repair_services", "Repair Services"),
            ("other_products", "Other Products"),
            ("other_services", "Other Services"),
        ],
        required=True,
        index=True,
    )
    billing_type = fields.Selection(
        [("b2c", "B2C"), ("b2b", "B2B")],
        index=True,
    )
    product_tmpl_id = fields.Many2one("product.template", string="Item", index=True)
    source_category = fields.Selection(
        [
            ("crm", "CRM"),
            ("walkin", "Walk-in"),
            ("doctor", "Doctor"),
            ("marketing", "Marketing"),
            ("outreach", "Outreach"),
            ("dealer", "Dealer"),
        ],
        index=True,
    )
    mrp_range_from = fields.Float()
    mrp_range_to = fields.Float()
    sharing_percent = fields.Float(required=True, default=0.0)
    billing_price = fields.Float()
    applicable_from = fields.Date()
    applicable_to = fields.Date()

    @api.constrains("sharing_percent", "mrp_range_from", "mrp_range_to")
    def _check_values(self):
        for rec in self:
            if rec.sharing_percent < 0 or rec.sharing_percent > 100:
                raise ValidationError("Sharing % must be between 0 and 100.")
            if rec.mrp_range_from and rec.mrp_range_from < 0:
                raise ValidationError("MRP range start cannot be negative.")
            if rec.mrp_range_to and rec.mrp_range_to < rec.mrp_range_from:
                raise ValidationError("MRP range end must be >= MRP range start.")

    @api.depends(
        "clinic_id",
        "apply_scope",
        "doctor_id",
        "doctor_id.apply_same_settings_all_clinics",
    )
    def _compute_clinic_display_name(self):
        for rec in self:
            if (
                rec.apply_scope == "standard"
                and rec.doctor_id.apply_same_settings_all_clinics
            ):
                rec.clinic_display_name = "All Clinics"
            else:
                rec.clinic_display_name = rec.clinic_id.display_name or ""

    @api.constrains("doctor_id", "apply_scope", "clinic_id")
    def _check_scope_clinic_membership(self):
        for rec in self:
            if not rec.doctor_id or not rec.clinic_id:
                continue
            if rec.apply_scope == "standard":
                allowed = rec.doctor_id.supported_clinic_ids
                if (
                    not rec.doctor_id.apply_same_settings_all_clinics
                    and allowed
                    and rec.clinic_id not in allowed
                ):
                    raise ValidationError(
                        "For Standard sharing, clinic must be part of Supported Clinics."
                    )
            elif rec.apply_scope == "different":
                allowed = rec.doctor_id.different_sharing_clinic_ids
                if rec.clinic_id not in allowed:
                    raise ValidationError(
                        "For Different sharing, clinic must be in Different Sharing Clinics."
                    )

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        doctor_id = vals.get("doctor_id") or self.env.context.get("default_doctor_id")
        apply_scope = vals.get("apply_scope") or self.env.context.get(
            "default_apply_scope", "standard"
        )
        if doctor_id and not vals.get("clinic_id"):
            doctor = self.env["resonnocare.doctor.profile"].browse(doctor_id)
            clinic = (
                doctor.different_sharing_clinic_ids[:1]
                if apply_scope == "different"
                else doctor.supported_clinic_ids[:1]
            )
            if clinic:
                vals["clinic_id"] = clinic.id
        if not vals.get("product_category"):
            vals["product_category"] = "hearing_device"
        if not vals.get("billing_type") and vals.get("clinic_id"):
            clinic = self.env["resonnocare.clinic"].browse(vals["clinic_id"])
            vals["billing_type"] = clinic._get_effective_billing_type()
        return vals

    @api.onchange("doctor_id", "apply_scope")
    def _onchange_doctor_scope(self):
        if not self.doctor_id:
            return
        domain = []
        clinic = False
        if self.apply_scope == "different":
            domain = [("id", "in", self.doctor_id.different_sharing_clinic_ids.ids)]
            clinic = self.doctor_id.different_sharing_clinic_ids[:1]
        else:
            if self.doctor_id.apply_same_settings_all_clinics:
                domain = []
                clinic = self.env["resonnocare.clinic"].search([], limit=1)
            else:
                domain = [("id", "in", self.doctor_id.supported_clinic_ids.ids)]
                clinic = self.doctor_id.supported_clinic_ids[:1]
        if clinic and not self.clinic_id:
            self.clinic_id = clinic.id
        return {"domain": {"clinic_id": domain}}

    @api.onchange("clinic_id")
    def _onchange_clinic_id(self):
        if self.clinic_id:
            self.billing_type = self.clinic_id._get_effective_billing_type()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            doctor_id = vals.get("doctor_id")
            doctor = (
                self.env["resonnocare.doctor.profile"].browse(doctor_id)
                if doctor_id
                else False
            )
            if not vals.get("product_category"):
                vals["product_category"] = "hearing_device"
            if not vals.get("rule_level"):
                if vals.get("source_category"):
                    vals["rule_level"] = "source"
                elif vals.get("product_tmpl_id"):
                    vals["rule_level"] = "item"
                elif vals.get("mrp_range_from") or vals.get("mrp_range_to"):
                    vals["rule_level"] = "mrp"
                else:
                    vals["rule_level"] = "flat"
            apply_scope = vals.get("apply_scope", "standard")
            if not vals.get("clinic_id") and doctor:
                clinic = (
                    doctor.different_sharing_clinic_ids[:1]
                    if apply_scope == "different"
                    else (
                        self.env["resonnocare.clinic"].search([], limit=1)
                        if doctor.apply_same_settings_all_clinics
                        else doctor.supported_clinic_ids[:1]
                    )
                )
                if clinic:
                    vals["clinic_id"] = clinic.id
            if not vals.get("billing_type") and vals.get("clinic_id"):
                clinic = self.env["resonnocare.clinic"].browse(vals["clinic_id"])
                vals["billing_type"] = clinic._get_effective_billing_type()
        return super().create(vals_list)
