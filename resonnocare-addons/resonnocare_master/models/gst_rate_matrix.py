import re
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResonnocareGstRateMatrix(models.Model):
    _name = "resonnocare.gst.rate.matrix"
    _description = "Resonnocare GST Rate Matrix"
    _order = "hsn_sac_code, id"

    name = fields.Char(string="Rule", compute="_compute_name", store=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    supply_type = fields.Selection(
        [("goods", "Goods"), ("services", "Services")],
        string="Type",
        required=True,
        default="goods",
    )
    hsn_sac_code = fields.Char(string="HSN/SAC", required=True, index=True)
    gst_rate = fields.Float(string="GST Rate (%)", required=True, default=0.0)
    is_exempt = fields.Boolean(string="Exempted", default=False)
    remarks = fields.Char(string="Remarks")

    _sql_constraints = [
        (
            "uniq_company_hsn_sac",
            "unique(company_id, hsn_sac_code)",
            "HSN/SAC must be unique per company.",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("hsn_sac_code"):
                vals["hsn_sac_code"] = self._normalize_hsn_sac(vals["hsn_sac_code"])
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("hsn_sac_code"):
            vals["hsn_sac_code"] = self._normalize_hsn_sac(vals["hsn_sac_code"])
        return super().write(vals)

    def _normalize_hsn_sac(self, code):
        return re.sub(r"[^0-9A-Za-z]", "", (code or "")).upper()

    @api.depends("supply_type", "hsn_sac_code", "gst_rate", "is_exempt")
    def _compute_name(self):
        for rec in self:
            tag = "Exempted" if rec.is_exempt else f"{rec.gst_rate:.2f}%"
            kind = "Goods" if rec.supply_type == "goods" else "Services"
            rec.name = f"{kind} | {rec.hsn_sac_code} | {tag}"

    @api.constrains("gst_rate")
    def _check_gst_rate(self):
        for rec in self:
            if rec.gst_rate < 0 or rec.gst_rate > 100:
                raise ValidationError("GST Rate must be between 0 and 100.")

    @api.constrains("hsn_sac_code")
    def _check_hsn_sac_code(self):
        for rec in self:
            if not rec._normalize_hsn_sac(rec.hsn_sac_code):
                raise ValidationError("HSN/SAC cannot be empty.")

    @api.constrains("is_exempt", "gst_rate")
    def _check_exempt_rate(self):
        for rec in self:
            if rec.is_exempt and rec.gst_rate != 0:
                raise ValidationError("Exempted rows must have GST Rate 0%.")
