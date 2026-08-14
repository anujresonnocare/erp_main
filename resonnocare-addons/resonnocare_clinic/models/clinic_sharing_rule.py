from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResonnocareClinicSharingRule(models.Model):
    _name = "resonnocare.clinic.sharing.rule"
    _description = "Clinic Sharing Rule"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    clinic_id = fields.Many2one(
        "resonnocare.clinic",
        required=True,
        ondelete="cascade",
        index=True,
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
    product_tmpl_id = fields.Many2one(
        "product.template",
        string="Item",
        index=True,
    )
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
    sharing_percent = fields.Float(required=True)
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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            clinic_id = vals.get("clinic_id")
            clinic = self.env["resonnocare.clinic"].browse(clinic_id) if clinic_id else False
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
            if not vals.get("billing_type") and clinic:
                vals["billing_type"] = clinic._get_effective_billing_type()
        return super().create(vals_list)
