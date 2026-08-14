from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResonnocareDiscountGrid(models.Model):
    _name = "resonnocare.discount.grid"
    _description = "Resonnocare Discount Grid"
    _order = "channel, mrp_from, id"

    name = fields.Char(string="Rule", compute="_compute_name", store=True)
    active = fields.Boolean(default=True)
    channel = fields.Selection(
        [("corporate", "Corporate"), ("hsis", "H / SIS")],
        required=True,
        index=True,
    )
    mrp_from = fields.Float(string="MRP From", required=True)
    mrp_to = fields.Float(string="MRP To")
    slab1_max = fields.Float(string="Slab 1 Max %", required=True)
    slab2_max = fields.Float(string="Slab 2 Max %", required=True)

    @api.depends("channel", "mrp_from", "mrp_to", "slab1_max", "slab2_max")
    def _compute_name(self):
        for rec in self:
            channel = "Corporate" if rec.channel == "corporate" else "H / SIS"
            upper = "Above" if not rec.mrp_to else f"{int(rec.mrp_to)}"
            rec.name = (
                f"{channel} | {int(rec.mrp_from)}-{upper} | "
                f"S1<= {rec.slab1_max:.0f}% | S2<= {rec.slab2_max:.0f}%"
            )

    @api.constrains("mrp_from", "mrp_to", "slab1_max", "slab2_max")
    def _check_values(self):
        for rec in self:
            if rec.mrp_from < 0:
                raise ValidationError("MRP From cannot be negative.")
            if rec.mrp_to and rec.mrp_to < rec.mrp_from:
                raise ValidationError("MRP To must be greater than or equal to MRP From.")
            if rec.slab1_max < 0 or rec.slab2_max < 0:
                raise ValidationError("Discount slab percentages cannot be negative.")
            if rec.slab2_max < rec.slab1_max:
                raise ValidationError("Slab 2 Max % must be greater than or equal to Slab 1 Max %.")

