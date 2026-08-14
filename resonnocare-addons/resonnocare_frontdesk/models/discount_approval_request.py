from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class ResonnocareDiscountApprovalRequest(models.Model):

    # hello test 
    _name = "resonnocare.discount.approval.request"
    _description = "Discount-cum-Lower Advance Approval Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Request ID",
        required=True,
        copy=False,
        default=lambda self: "New",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )

    
    required_approval_level = fields.Selection(
        [
            ("none", "No Approval Required"),
            ("manager", "Manager Approval"),
            ("admin", "Admin Approval"),
        ],
        string="Required Approval Level",
        compute="_compute_required_approval_level",
        store=True,
        readonly=True,
    )

    sale_order_id = fields.Many2one(
        "sale.order", string="Sale Order", required=True, ondelete="cascade", tracking=True
    )
    appointment_id = fields.Many2one(
        "resonnocare.appointment",
        string="Appointment",
        ondelete="set null",
        tracking=True,
    )
    clinic_id = fields.Many2one(
        "resonnocare.clinic",
        string="Clinic",
        related="sale_order_id.clinic_id",
        store=True,
        readonly=True,
    )
    patient_id = fields.Many2one(
        "res.partner",
        string="Patient",
        related="sale_order_id.patient_id",
        store=True,
        readonly=True,
    )
    patient_code = fields.Char(
        string="Patient ID",
        related="patient_id.patient_id",
        store=True,
        readonly=True,
    )
    referral_source = fields.Selection(
        related="patient_id.referral_source",
        string="Referral Source",
        store=True,
        readonly=True,
    )
    referral_doctor_name = fields.Char(
        string="Referral Doctor Name",
        related="patient_id.referring_doctor",
        store=True,
        readonly=True,
    )

    hearing_aid_left = fields.Char(string="Hearing Aid Name - Left")
    hearing_aid_right = fields.Char(string="Hearing Aid Name - Right")
    ha_brand = fields.Char(string="HA Brand")
    no_of_ha = fields.Integer(
        string="No. of HA", compute="_compute_discount_metrics", store=True
    )
    total_ha_mrp = fields.Monetary(
        string="Total HA MRP", compute="_compute_discount_metrics", store=True
    )
    max_discount_pct_allowed = fields.Float(
        string="Max Discount % allowed as per Clinic Grid",
        compute="_compute_discount_metrics",
        store=True,
    )
    max_discount_value_allowed = fields.Monetary(
        string="Max Discount Value allowed as per Clinic Grid",
        compute="_compute_discount_metrics",
        store=True,
    )
    discount_value_requested = fields.Monetary(
        string="Discount Value requested by the clinic",
        tracking=True,
    )
    discount_pct_requested = fields.Float(
        string="Discount % requested by the clinic",
        tracking=True,
    )

    ha_discount_pct = fields.Float(
        string="HA Discount %",
        tracking=True,
        help="Enter the discount percentage applicable to hearing aids."
    )

    ha_discount_value = fields.Monetary(
        string="HA Discount Value",
        tracking=True,
        default=0.0,
    )

    min_advance_required = fields.Monetary(
        string="Min advance required for order",
        compute="_compute_discount_metrics",
        store=True,
    )
    lower_advance_requested = fields.Monetary(
        string="Lower value of advance requested by the clinic",
        tracking=True,
    )
    discount_absorbed_by_doctor = fields.Monetary(
        string="Discount value to be absorbed by the doctor", tracking=True
    )

    requested_by_id = fields.Many2one(
        "res.users",
        string="Requested By",
        default=lambda self: self.env.user,
        readonly=True,
    )
    approved_by_id = fields.Many2one("res.users", string="Approved By", readonly=True)
    approved_on = fields.Datetime(string="Approved On", readonly=True)
    rejection_reason = fields.Text(string="Rejection Reason")

    currency_id = fields.Many2one(
        "res.currency",
        related="sale_order_id.currency_id",
        string="Currency",
        readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code(
                        "resonnocare.discount.approval.request"
                    )
                    or "New"
                )
            if vals.get("sale_order_id"):
                sale = self.env["sale.order"].browse(vals["sale_order_id"])
                auto_vals = self._prepare_auto_values_from_sale_order(
                    sale
                )
                for key, value in auto_vals.items():
                    if not vals.get(key):
                        vals[key] = value
                metrics = self._get_discount_metrics_from_sale_order(sale)
                if not vals.get("discount_value_requested"):
                    vals["discount_value_requested"] = metrics["discount_value_requested"]
                if not vals.get("discount_pct_requested"):
                    vals["discount_pct_requested"] = metrics["discount_pct_requested"]
        return super().create(vals_list)

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        sale_order_id = vals.get("sale_order_id") or self.env.context.get("default_sale_order_id")
        if sale_order_id:
            sale = self.env["sale.order"].browse(sale_order_id)
            auto_vals = self._prepare_auto_values_from_sale_order(sale)
            vals.update({k: v for k, v in auto_vals.items() if k in fields_list or not fields_list})
            metrics = self._get_discount_metrics_from_sale_order(sale)
            vals["discount_value_requested"] = metrics["discount_value_requested"]
            vals["discount_pct_requested"] = metrics["discount_pct_requested"]
        return vals

    def _prepare_auto_values_from_sale_order(self, sale):
        if not sale:
            return {}
        device_lines = sale.order_line.filtered(
            lambda l: l.product_id and not l.display_type and not l.is_downpayment
            and getattr(l.product_id, "type", "") in ("product", "consu")
        )
        left_name = device_lines[:1].product_id.display_name if device_lines else False
        right_name = device_lines[1:2].product_id.display_name if len(device_lines) > 1 else False

        brands = []
        for line in device_lines:
            product = line.product_id
            brand = ""
            if hasattr(product, "manufacturer_id") and product.manufacturer_id:
                brand = product.manufacturer_id.name or ""
            elif product.product_tmpl_id and getattr(product.product_tmpl_id, "manufacturer_id", False):
                brand = product.product_tmpl_id.manufacturer_id.name or ""
            if brand and brand not in brands:
                brands.append(brand)

        return {
            "hearing_aid_left": left_name,
            "hearing_aid_right": right_name,
            "ha_brand": ", ".join(brands) if brands else False,
            "lower_advance_requested": (sale.amount_total or 0.0) * 0.30,
        }

    @api.model
    def _get_discount_metrics_from_sale_order(self, sale):
        if not sale:
            return {
                "no_of_ha": 0,
                "total_ha_mrp": 0.0,
                "max_discount_pct_allowed": 0.0,
                "max_discount_value_allowed": 0.0,
                "discount_value_requested": 0.0,
                "discount_pct_requested": 0.0,
                "min_advance_required": 0.0,
            }
        lines = sale.order_line.filtered(
            lambda l: l.product_id and not l.display_type and not l.is_downpayment
        )
        device_lines = lines.filtered(
            lambda l: getattr(l.product_id, "type", "") in ("product", "consu")
        )
        gross = 0.0
        discount_value = 0.0
        for line in lines:
            qty = line.product_uom_qty or 0.0
            unit_price = line.price_unit or 0.0
            base_mrp = getattr(line, "discount_reference_mrp", 0.0) or 0.0
            
            # Calculate base MRP (pre-tax amount before discount)
            line_base_mrp = (base_mrp if base_mrp > 0.0 else unit_price) * qty
            gross += line_base_mrp

            # Get the pre-tax subtotal (after discount)
            if line.price_subtotal:
                line_subtotal = line.price_subtotal
            else:
                line_subtotal = unit_price * qty * (1.0 - (line.discount or 0.0) / 100.0)
            
            # Discount value is the difference between base MRP and actual subtotal
            line_discount_value = max(line_base_mrp - line_subtotal, 0.0)
            discount_value += line_discount_value
        max_pct = 0.0
        grid_lines = lines.filtered(lambda l: l.discount_grid_id)
        if grid_lines:
            max_pct = max((l.discount_grid_id.slab2_max or 0.0) for l in grid_lines)
        return {
            "no_of_ha": int(sum(l.product_uom_qty or 0.0 for l in device_lines)),
            "total_ha_mrp": gross,
            "max_discount_pct_allowed": max_pct,
            "max_discount_value_allowed": gross * (max_pct / 100.0) if gross else 0.0,
            "discount_value_requested": discount_value,
            "discount_pct_requested": (discount_value / gross * 100.0) if gross else 0.0,
            "min_advance_required": (sale.amount_total or 0.0) * 0.30,
        }

    @api.onchange("sale_order_id")
    def _onchange_sale_order_id_autofill(self):
        for rec in self:
            if not rec.sale_order_id:
                continue
            auto_vals = rec._prepare_auto_values_from_sale_order(rec.sale_order_id)
            if not rec.hearing_aid_left and auto_vals.get("hearing_aid_left"):
                rec.hearing_aid_left = auto_vals.get("hearing_aid_left")
            if not rec.hearing_aid_right and auto_vals.get("hearing_aid_right"):
                rec.hearing_aid_right = auto_vals.get("hearing_aid_right")
            if not rec.ha_brand and auto_vals.get("ha_brand"):
                rec.ha_brand = auto_vals.get("ha_brand")
            if not rec.lower_advance_requested and auto_vals.get("lower_advance_requested"):
                rec.lower_advance_requested = auto_vals.get("lower_advance_requested")
            # Force immediate values in form (without requiring save).
            metrics = rec._get_discount_metrics_from_sale_order(rec.sale_order_id)
            rec.no_of_ha = metrics["no_of_ha"]
            rec.total_ha_mrp = metrics["total_ha_mrp"]
            rec.max_discount_pct_allowed = metrics["max_discount_pct_allowed"]
            rec.max_discount_value_allowed = metrics["max_discount_value_allowed"]
            rec.discount_value_requested = metrics["discount_value_requested"]
            rec.discount_pct_requested = metrics["discount_pct_requested"]
            rec.min_advance_required = metrics["min_advance_required"]
            rec._compute_required_approval_level()

    @api.depends(
        "sale_order_id.order_line.discount",
        "sale_order_id.order_line.price_unit",
        "sale_order_id.order_line.product_uom_qty",
        "sale_order_id.order_line.discount_grid_id.slab2_max",
        "sale_order_id.order_line.product_id",
        "sale_order_id.amount_total",
    )
    def _compute_discount_metrics(self):
        for rec in self:
            metrics = rec._get_discount_metrics_from_sale_order(rec.sale_order_id)
            rec.no_of_ha = metrics["no_of_ha"]
            rec.total_ha_mrp = metrics["total_ha_mrp"]
            rec.max_discount_pct_allowed = metrics["max_discount_pct_allowed"]
            rec.max_discount_value_allowed = metrics["max_discount_value_allowed"]
            rec.min_advance_required = metrics["min_advance_required"]

    @api.depends(
        "sale_order_id.order_line.discount",
        "sale_order_id.order_line.discount_grid_id",
        "sale_order_id.order_line.discount_grid_id.slab1_max",
        "sale_order_id.order_line.discount_grid_id.slab2_max",
        "sale_order_id.order_line.product_id",
    )
    def _compute_required_approval_level(self):
        for rec in self:
            level = "none"
            lines = rec.sale_order_id.order_line.filtered(
                lambda l: l.product_id and l.discount_grid_id and not l.display_type
            )
            for line in lines:
                discount = line.discount or 0.0
                slab1 = line.discount_grid_id.slab1_max or 0.0
                slab2 = line.discount_grid_id.slab2_max or 0.0
                if discount > slab2:
                    level = "admin"
                    break
                if discount > slab1:
                    level = "manager"
            rec.required_approval_level = level

    @api.constrains("lower_advance_requested", "min_advance_required", "sale_order_id")
    def _check_lower_advance(self):
        for rec in self:
            if rec.lower_advance_requested and rec.lower_advance_requested < 0:
                raise ValidationError("Lower advance requested cannot be negative.")
            if (
                rec.lower_advance_requested
                and rec.sale_order_id
                and rec.lower_advance_requested > (rec.sale_order_id.amount_total or 0.0)
            ):
                raise ValidationError(
                    "Lower advance requested cannot exceed sale order total."
                )

    def action_submit(self):
        for rec in self:
            if rec.state != "draft":
                continue
            if not rec.lower_advance_requested:
                raise UserError("Please enter the lower advance requested value before submit.")
            if rec.no_of_ha > 0 and not rec.ha_discount_pct:
                raise UserError(
                    "HA Discount % is mandatory when hearing aids are present in the sale order. "
                    "Please enter the HA Discount % before submitting."
                )
            rec.state = "submitted"

    def action_approve(self):
        for rec in self:
            if rec.state != "submitted":
                continue
            rec.write(
                {
                    "state": "approved",
                    "approved_by_id": self.env.user.id,
                    "approved_on": fields.Datetime.now(),
                    "rejection_reason": False,
                }
            )

    def action_reject(self):
        for rec in self:
            if rec.state != "submitted":
                continue
            rec.write(
                {
                    "state": "rejected",
                    "approved_by_id": False,
                    "approved_on": False,
                }
            )

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_reset_draft(self):
        self.write(
            {
                "state": "draft",
                "approved_by_id": False,
                "approved_on": False,
            }
        )
