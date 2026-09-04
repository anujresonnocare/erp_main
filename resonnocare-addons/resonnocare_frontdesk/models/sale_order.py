from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import re

import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"

    patient_id = fields.Many2one(
        "res.partner", string="Patient", domain=[("is_patient", "=", True)]
    )

    clinic_id = fields.Many2one(
        "resonnocare.clinic",
        string="Clinic",
        index=True,
        readonly=True,
    )
    discount_approval_request_ids = fields.One2many(
        "resonnocare.discount.approval.request",
        "sale_order_id",
        string="Discount Requests",
    )
    discount_approval_request_count = fields.Integer(
        string="Discount Requests",
        compute="_compute_discount_approval_request_count",
    )
    advance_approval_request_ids = fields.One2many(
        "resonnocare.advance.approval.request",
        "sale_order_id",
        string="Min Advance Requests",
    )
    advance_approval_request_count = fields.Integer(
        string="Min Advance Requests",
        compute="_compute_advance_approval_request_count",
    )
    return_request_ids = fields.One2many(
        "resonnocare.sale.return.request",
        "sale_order_id",
        string="Return Requests",
    )
    return_request_count = fields.Integer(
        string="Return Requests Count",
        compute="_compute_return_request_count",
    )
    show_create_contract_button = fields.Boolean(
        string="Show Create Contract Button",
        compute="_compute_show_create_contract_button",
        store=False,
    )

    def _compute_discount_approval_request_count(self):
        grouped = self.env["resonnocare.discount.approval.request"].read_group(
            [("sale_order_id", "in", self.ids)],
            ["sale_order_id"],
            ["sale_order_id"],
        )
        mapped = {row["sale_order_id"][0]: row["sale_order_id_count"] for row in grouped}
        for order in self:
            order.discount_approval_request_count = mapped.get(order.id, 0)

    def _compute_advance_approval_request_count(self):
        grouped = self.env["resonnocare.advance.approval.request"].read_group(
            [("sale_order_id", "in", self.ids)],
            ["sale_order_id"],
            ["sale_order_id"],
        )
        mapped = {row["sale_order_id"][0]: row["sale_order_id_count"] for row in grouped}
        for order in self:
            order.advance_approval_request_count = mapped.get(order.id, 0)

    def _compute_return_request_count(self):
        grouped = self.env["resonnocare.sale.return.request"].read_group(
            [("sale_order_id", "in", self.ids)],
            ["sale_order_id"],
            ["sale_order_id"],
        )
        mapped = {row["sale_order_id"][0]: row["sale_order_id_count"] for row in grouped}
        for order in self:
            order.return_request_count = mapped.get(order.id, 0)

    @api.depends("invoice_ids.move_type", "invoice_ids.state")
    def _compute_show_create_contract_button(self):
        for order in self:
            flow = order._get_sale_flow_type() if order.id else False
            is_device_flow = flow == "device"
            existing_customer_invoices = order.invoice_ids.filtered(
                lambda inv: inv.move_type == "out_invoice" and inv.state != "cancel"
            )
            is_first_invoice = not bool(existing_customer_invoices)
            order.show_create_contract_button = bool(is_device_flow and is_first_invoice)

    # def _get_required_discount_approval_level(self):
    #     self.ensure_one()
    #     required_level = "none"
    #     product_lines = self.order_line.filtered(lambda l: l.product_id and not l.display_type)

    #     # Primary path: rely on precomputed slab on lines.
    #     for line in product_lines:
    #         if line.discount_slab == "slab3":
    #             return "admin"
    #         if line.discount_slab == "slab2":
    #             required_level = "manager"

    #     Grid = self.env["resonnocare.discount.grid"]
    #     Diag = self.env["resonnocare.diagnostic.item"]
    #     ClinicDiag = self.env["resonnocare.clinic.diagnostic"]

    #     for line in product_lines:
    #         channel = line._get_discount_channel()
    #         ptype = getattr(line.product_id, "type", False)
    #         clinic = line.order_id.clinic_id or line.order_id.patient_id.clinic_id

    #         if ptype == "service":
    #             mrp = 0.0
    #             if clinic:
    #                 diag = Diag.search([("product_id", "=", line.product_id.id)], limit=1)
    #                 if diag:
    #                     clinic_diag = ClinicDiag.search(
    #                         [
    #                             ("clinic_id", "=", clinic.id),
    #                             ("diagnostic_item_id", "=", diag.id),
    #                         ],
    #                         limit=1,
    #                     )
    #                     mrp = clinic_diag.mrp or 0.0
    #         else:
    #             mrp = line.product_id.lst_price or 0.0

    #         grid = Grid.search(
    #             [
    #                 ("active", "=", True),
    #                 ("channel", "=", channel),
    #                 ("mrp_from", "<=", mrp),
    #                 "|",
    #                 ("mrp_to", "=", 0),
    #                 ("mrp_to", ">=", mrp),
    #             ],
    #             order="mrp_from desc, id desc",
    #             limit=1,
    #         )
    #         if not grid:
    #             continue

    #         discount = line.discount or 0.0
    #         if discount > (grid.slab2_max or 0.0):
    #             required_level = "admin"
    #             break
    #         if discount > (grid.slab1_max or 0.0):
    #             required_level = "manager"
    #     return required_level




    def _get_required_discount_approval_level(self):
        _logger.info("Starting _get_required_discount_approval_level()")
        self.ensure_one()
        _logger.info("ensure_one() completed for sale order ID: %s", self.id)

        required_level = "none"
        _logger.info("Initial required_level: %s", required_level)

        product_lines = self.order_line.filtered(
            lambda l: l.product_id and not l.display_type
        )
        _logger.info(
            "Filtered product lines count: %s, line IDs: %s",
            len(product_lines),
            product_lines.ids,
        )

        # Primary path: rely on precomputed slab on lines.
        _logger.info("Checking precomputed discount slabs on order lines")

        for line in product_lines:
            _logger.info(
                "Checking line ID: %s, product: %s, discount_slab: %s",
                line.id,
                line.product_id.display_name,
                line.discount_slab,
            )

            if line.discount_slab == "slab3":
                _logger.info(
                    "Line ID %s has slab3. Required approval level: admin",
                    line.id,
                )
                return "admin"

            if line.discount_slab == "slab2":
                _logger.info(
                    "Line ID %s has slab2. Setting required_level to manager",
                    line.id,
                )
                required_level = "manager"

        _logger.info(
            "After precomputed slab check, required_level: %s",
            required_level,
        )

        Grid = self.env["resonnocare.discount.grid"]
        _logger.info("Loaded discount grid model: %s", Grid)

        Diag = self.env["resonnocare.diagnostic.item"]
        _logger.info("Loaded diagnostic item model: %s", Diag)

        ClinicDiag = self.env["resonnocare.clinic.diagnostic"]
        _logger.info("Loaded clinic diagnostic model: %s", ClinicDiag)

        for line in product_lines:
            _logger.info(
                "Processing line ID: %s, product: %s",
                line.id,
                line.product_id.display_name,
            )

            channel = line._get_discount_channel()
            _logger.info(
                "Line ID %s discount channel: %s",
                line.id,
                channel,
            )

            ptype = getattr(line.product_id, "type", False)
            _logger.info(
                "Line ID %s product type: %s",
                line.id,
                ptype,
            )

            clinic = (
                line.order_id.clinic_id
                or line.order_id.patient_id.clinic_id
            )
            _logger.info(
                "Line ID %s clinic: %s (ID: %s)",
                line.id,
                clinic.display_name if clinic else False,
                clinic.id if clinic else False,
            )

            if ptype == "service":
                _logger.info(
                    "Line ID %s is a service product",
                    line.id,
                )

                mrp = 0.0
                _logger.info(
                    "Initial MRP for line ID %s: %s",
                    line.id,
                    mrp,
                )

                if clinic:
                    _logger.info(
                        "Clinic found for line ID %s. Searching diagnostic item",
                        line.id,
                    )

                    diag = Diag.search(
                        [
                            ("product_id", "=", line.product_id.id)
                        ],
                        limit=1,
                    )
                    _logger.info(
                        "Diagnostic item search result for line ID %s: %s (ID: %s)",
                        line.id,
                        diag.display_name if diag else False,
                        diag.id if diag else False,
                    )

                    if diag:
                        _logger.info(
                            "Diagnostic item found. Searching clinic diagnostic for line ID %s",
                            line.id,
                        )

                        clinic_diag = ClinicDiag.search(
                            [
                                ("clinic_id", "=", clinic.id),
                                ("diagnostic_item_id", "=", diag.id),
                            ],
                            limit=1,
                        )
                        _logger.info(
                            "Clinic diagnostic search result for line ID %s: %s (ID: %s)",
                            line.id,
                            clinic_diag.display_name if clinic_diag else False,
                            clinic_diag.id if clinic_diag else False,
                        )

                        mrp = clinic_diag.mrp or 0.0
                        _logger.info(
                            "MRP calculated from clinic diagnostic for line ID %s: %s",
                            line.id,
                            mrp,
                        )
            else:
                _logger.info(
                    "Line ID %s is not a service product",
                    line.id,
                )

                mrp = line.product_id.lst_price or 0.0
                _logger.info(
                    "MRP taken from product lst_price for line ID %s: %s",
                    line.id,
                    mrp,
                )

            _logger.info(
                "Searching discount grid for line ID %s with channel=%s, mrp=%s",
                line.id,
                channel,
                mrp,
            )

            grid = Grid.search(
                [
                    ("active", "=", True),
                    ("channel", "=", channel),
                    ("mrp_from", "<=", mrp),
                    "|",
                    ("mrp_to", "=", 0),
                    ("mrp_to", ">=", mrp),
                ],
                order="mrp_from desc, id desc",
                limit=1,
            )
            _logger.info(
                "Discount grid search result for line ID %s: %s (ID: %s)",
                line.id,
                grid.display_name if grid else False,
                grid.id if grid else False,
            )

            if not grid:
                _logger.info(
                    "No discount grid found for line ID %s. Continuing to next line.",
                    line.id,
                )
                continue

            discount = line.discount or 0.0
            _logger.info(
                "Line ID %s discount: %s",
                line.id,
                discount,
            )

            slab2_max = grid.slab2_max or 0.0
            _logger.info(
                "Line ID %s grid slab2_max: %s",
                line.id,
                slab2_max,
            )

            if discount > slab2_max:
                _logger.info(
                    "Line ID %s discount %s > slab2_max %s. "
                    "Required approval level: admin",
                    line.id,
                    discount,
                    slab2_max,
                )
                required_level = "admin"
                break

            slab1_max = grid.slab1_max or 0.0
            _logger.info(
                "Line ID %s grid slab1_max: %s",
                line.id,
                slab1_max,
            )

            if discount > slab1_max:
                _logger.info(
                    "Line ID %s discount %s > slab1_max %s. "
                    "Setting required_level to manager",
                    line.id,
                    discount,
                    slab1_max,
                )
                required_level = "manager"

            _logger.info(
                "Completed processing line ID %s. Current required_level: %s",
                line.id,
                required_level,
            )

        _logger.info(
            "Completed _get_required_discount_approval_level() for sale order ID %s. "
            "Final required_level: %s",
            self.id,
            required_level,
        )

        return required_level

    def _check_discount_approval_before_confirm(self):
        for order in self:
            required_level = order._get_required_discount_approval_level()
            if required_level == "none":
                continue

            allowed_levels = ["admin"] if required_level == "admin" else ["manager", "admin"]
            approved_request = self.env["resonnocare.discount.approval.request"].search(
                [
                    ("sale_order_id", "=", order.id),
                    ("state", "=", "approved"),
                    ("required_approval_level", "in", allowed_levels),
                ],
                order="id desc",
                limit=1,
            )
            if not approved_request:
                level_label = "Manager" if required_level == "manager" else "Admin"
                raise ValidationError(
                    f"Discount approval missing: {level_label} approval is required.\n"
                    "Create and approve a Discount Request before creating invoice for this sale order."
                )

    def action_open_discount_requests(self):
        self.ensure_one()
        metrics = self.env["resonnocare.discount.approval.request"]._get_discount_metrics_from_sale_order(self)
        return {
            "type": "ir.actions.act_window",
            "name": "Discount Requests",
            "res_model": "resonnocare.discount.approval.request",
            "view_mode": "list,form",
            "domain": [("sale_order_id", "=", self.id)],
            "context": {
                "default_sale_order_id": self.id,
                "default_discount_value_requested": metrics["discount_value_requested"],
                "default_discount_pct_requested": metrics["discount_pct_requested"],
                "default_lower_advance_requested": (self.amount_total or 0.0) * 0.30,
            },
            "target": "current",
        }

    def action_open_advance_requests(self):
        self.ensure_one()
        min_advance = (self.amount_total or 0.0) * 0.30
        return {
            "type": "ir.actions.act_window",
            "name": "Min Advance Requests",
            "res_model": "resonnocare.advance.approval.request",
            "view_mode": "list,form",
            "domain": [("sale_order_id", "=", self.id)],
            "context": {
                "default_sale_order_id": self.id,
                "default_requested_min_advance": min_advance,
            },
            "target": "current",
        }

    def action_view_return_requests(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Return Requests",
            "res_model": "resonnocare.sale.return.request",
            "view_mode": "list,form",
            "domain": [("sale_order_id", "=", self.id)],
            "context": {
                "default_sale_order_id": self.id,
            },
            "target": "current",
        }

    @api.model_create_multi
    def create(self, vals_list):
        user_clinic = self.env.user.sudo().clinic_id or self.env.user.sudo().employee_id.clinic_id
        for vals in vals_list:
            if not vals.get("clinic_id"):
                patient_id = vals.get("patient_id") or vals.get("partner_id")
                if patient_id:
                    patient = self.env["res.partner"].browse(patient_id)
                    if patient.is_patient and patient.clinic_id:
                        vals["clinic_id"] = patient.clinic_id.id

            if not vals.get("clinic_id"):
                if user_clinic:
                    vals["clinic_id"] = user_clinic.id

        return super().create(vals_list)

    # ✅ ADD THIS METHOD
    @api.onchange("patient_id")
    def _onchange_patient_clinic_warehouse(self):
        """
        Auto-set warehouse based on patient's clinic.

        Logic:
        - Patient has clinic_id
        - Clinic has warehouse_id
        - Sale order should use that warehouse for stock operations
        """
        if self.patient_id and self.patient_id.is_patient:
            clinic = self.patient_id.clinic_id

            if clinic and clinic.warehouse_id:
                self.warehouse_id = clinic.warehouse_id
                self.clinic_id = clinic

                # Optional: Show message to user
                return {
                    "warning": {
                        "title": "Warehouse Set",
                        "message": f"Warehouse automatically set to: {clinic.warehouse_id.name}",
                    }
                }

    def action_confirm(self):
        """Validate patient and warehouse before confirmation"""
        for order in self:
            if not order.partner_id or not order.partner_id.is_patient:
                raise ValidationError("Please select a Patient before confirming the sale.")

            # sync patient_id automatically
            order.patient_id = order.partner_id

            # ✅ CHECK FOR PENDING MINIMUM ADVANCE REQUESTS
            pending_advance_requests = self.env["resonnocare.advance.approval.request"].search([
                ("sale_order_id", "=", order.id),
                ("state", "in", ("draft", "submitted")),
            ])
            if pending_advance_requests:
                pending_count = len(pending_advance_requests)
                request_ids = ", ".join([req.name for req in pending_advance_requests])
                raise ValidationError(
                    f"Cannot confirm Sale Order '{order.name}': "
                    f"There are {pending_count} pending minimum advance request(s) that must be approved first.\n"
                    f"Pending Requests: {request_ids}\n\n"
                    f"Please approve or cancel all pending minimum advance requests before confirming this sale order."
                )

            # ✅ ENSURE PATIENT HAS A CLINIC
            if order.patient_id.is_patient and not order.patient_id.clinic_id:
                # Use sudo() to ensure we bypass read restrictions on user/clinic during validation
                user_clinic = self.env.user.sudo().clinic_id or self.env.user.sudo().employee_id.clinic_id
                if user_clinic:
                    order.patient_id.sudo().write({"clinic_id": user_clinic.id})
                    order.patient_id.invalidate_recordset(["clinic_id"])
                else:
                    raise ValidationError(
                        f"Patient {order.patient_id.name} is not assigned to any clinic, "
                        "and your user account also doesn't have an assigned clinic. "
                        "Please contact admin."
                    )

            # ✅ VALIDATE WAREHOUSE
            if order.patient_id.is_patient:
                # Re-read clinic after potential auto-assignment
                clinic = order.patient_id.clinic_id

                if not clinic:
                    raise ValidationError(
                        f"Patient {order.patient_id.name} is not assigned to any clinic. "
                        "Cannot process sale order."
                    )

                if not clinic.warehouse_id:
                    raise ValidationError(
                        f"Clinic {clinic.name} does not have a warehouse configured. "
                        "Please contact admin."
                    )

                # ✅ ENSURE CORRECT WAREHOUSE
                if order.warehouse_id != clinic.warehouse_id:
                    order.warehouse_id = clinic.warehouse_id
                if order.clinic_id != clinic:
                    order.clinic_id = clinic

        return super().action_confirm()

    def _get_sale_flow_type(self):
        """Infer whether this SO belongs to service or device appointment flow."""
        self.ensure_one()
        appt = self.env["resonnocare.appointment"].search(
            [("sale_order_id", "=", self.id)],
            order="parent_appointment_id asc, id asc",
            limit=1,
        )
        return appt.sale_type if appt else False

    @api.constrains("order_line")
    def _check_line_product_mix_by_flow(self):
        for order in self:
            flow = order._get_sale_flow_type()
            if flow not in ("service", "device"):
                continue

            lines = order.order_line.filtered(lambda l: l.product_id and not l.display_type)
            if not lines:
                continue

            if flow == "service":
                # Keep service flow strict: only service products are allowed.
                invalid = lines.filtered(lambda l: l.product_id.type != "service")
                if invalid:
                    raise ValidationError(
                        "This Sale Order is for Diagnostic/Service flow. "
                        "Device/HA products are not allowed."
                    )
            else:
                invalid = lines.filtered(
                    lambda l: l.product_id.type == "service"
                    or getattr(l.product_id.product_tmpl_id, "item_type", False) == "diagnostic_service"
                )
                if invalid:
                    raise ValidationError(
                        "This Sale Order is for Device/HA flow. "
                        "Diagnostic service products are not allowed."
                    )

    def write(self, vals):
        return super().write(vals)

    def _create_invoices(self, grouped=False, final=False, date=None):
        # Keep approval validation only at invoice creation.
        self._check_discount_approval_before_confirm()
        return super()._create_invoices(grouped=grouped, final=final, date=date)

    def action_create_invoice(self):
        # Block at initial button click (before opening advance payment popup).
        self._check_discount_approval_before_confirm()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "sale.action_view_sale_advance_payment_inv"
        )
        action_context = dict(self.env.context or {})
        action_context.update(
            {
                "active_model": "sale.order",
                "active_ids": self.ids,
                "active_id": self.id,
            }
        )
        action["context"] = action_context
        return action

    def action_print_final_invoice(self):
        self.ensure_one()
        doc = self.env["resonnocare.final.invoice"].create_or_refresh_from_sale_order(self)
        return doc.action_print_document()

    def action_view_contract(self):
        self.ensure_one()
        customer_invoices = self.invoice_ids.filtered(
            lambda inv: inv.move_type == "out_invoice" and inv.state != "cancel"
        )
        if not customer_invoices:
            raise UserError(
                "Contract cannot be previewed before invoice creation. Please create customer invoice first."
            )

        total_paid = 0.0
        posted_invoices = customer_invoices.filtered(lambda inv: inv.state == "posted")
        for inv in posted_invoices:
            if hasattr(inv, "_get_contract_advance_paid"):
                total_paid += inv._get_contract_advance_paid()
            else:
                total_paid += max((inv.amount_total or 0.0) - (inv.amount_residual or 0.0), 0.0)

        # Default contract release threshold is 30%.
        required_paid = (self.amount_total or 0.0) * 0.30

        # If a Min Advance Request is approved for this SO, use approved minimum instead.
        approved_min_request = self.env["resonnocare.advance.approval.request"].search(
            [
                ("sale_order_id", "=", self.id),
                ("state", "=", "approved"),
            ],
            order="id desc",
            limit=1,
        )
        if approved_min_request and approved_min_request.requested_min_advance:
            required_paid = approved_min_request.requested_min_advance

        if total_paid < required_paid:
            raise UserError(
                "Contract cannot be previewed yet.\n"
                f"Required Advance: {required_paid:.2f}\n"
                f"Paid Advance: {total_paid:.2f}\n"
                "Please collect required advance, or get Min Advance Request approved."
            )

        candidate_invoices = customer_invoices.filtered(
            lambda inv: inv.move_type == "out_invoice"
            and inv.state != "cancel"
            and hasattr(inv, "_is_downpayment_invoice")
            and inv._is_downpayment_invoice()
        )
        if not candidate_invoices:
            raise UserError(
                "No down payment invoice found to preview contract for this sale order."
            )
        invoice = candidate_invoices.sorted(
            lambda inv: (inv.invoice_date or inv.date or fields.Date.today(), inv.id)
        )[-1]
        return invoice.action_view_contract()

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        if self.clinic_id:
            invoice_vals["clinic_id"] = self.clinic_id.id
        return invoice_vals


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    discount_channel = fields.Selection(
        [("corporate", "Corporate"), ("hsis", "H / SIS")],
        string="Discount Channel",
        compute="_compute_discount_grid_meta",
        store=True,
    )
    discount_grid_id = fields.Many2one(
        "resonnocare.discount.grid",
        string="Discount Grid Rule",
        compute="_compute_discount_grid_meta",
        store=True,
    )
    discount_slab = fields.Selection(
        [("slab1", "Slab 1"), ("slab2", "Slab 2"), ("slab3", "Slab 3")],
        string="Discount Slab",
        compute="_compute_discount_slab",
        store=True,
    )
    discount_base_mrp = fields.Float(
        string="Discount Base MRP",
        compute="_compute_discount_grid_meta",
        store=True,
    )
    discount_reference_mrp = fields.Float(
        string="Discount Reference MRP",
        compute="_compute_discount_grid_meta",
        store=True,
    )

    discount_type = fields.Selection(
        [("percent", "Percentage"), ("fixed", "Fixed Amount")],
        string="Discount Type",
        default="percent",
    )
    discount_fixed = fields.Float(
        string="Discount (₹)",
        digits="Product Price",
        help="Fixed discount amount per unit in currency.",
    )

    @api.onchange("discount_type", "discount_fixed")
    def _onchange_discount_fixed_to_pct(self):
        """When user enters a fixed discount amount, convert to percentage."""
        for line in self:
            if line.discount_type != "fixed":
                continue
            price = line.price_unit or 0.0
            if price > 0:
                line.discount = (line.discount_fixed / price) * 100.0
            else:
                line.discount = 0.0

    @api.onchange("discount", "discount_type", "price_unit")
    def _onchange_discount_pct_to_fixed(self):
        """When user enters a percentage discount, compute the fixed amount."""
        for line in self:
            if line.discount_type != "percent":
                continue
            price = line.price_unit or 0.0
            line.discount_fixed = price * (line.discount or 0.0) / 100.0

    def _normalize_hsn_sac(self, code):
        return re.sub(r"[^0-9A-Za-z]", "", (code or "")).upper()

    @api.onchange("order_id")
    def _onchange_order_id_product_domain_by_flow(self):
        self.ensure_one()
        if not self.order_id:
            return {}
        flow = self.order_id._get_sale_flow_type()
        if flow == "service":
            return {
                "domain": {
                    "product_id": [("sale_ok", "=", True), ("active", "=", True), ("type", "=", "service")]
                }
            }
        if flow == "device":
            return {
                "domain": {
                    "product_id": [
                        ("sale_ok", "=", True),
                        ("active", "=", True),
                        ("type", "!=", "service"),
                        ("product_tmpl_id.item_type", "!=", "diagnostic_service"),
                    ]
                }
            }
        return {}

    @api.onchange("product_id")
    def _onchange_product_id_validate_flow(self):
        self.ensure_one()
        if not self.order_id or not self.product_id:
            return
        flow = self.order_id._get_sale_flow_type()
        if flow == "service" and self.product_id.type != "service":
            self.product_id = False
            return {
                "warning": {
                    "title": "Invalid Product",
                    "message": "Diagnostic/Service flow allows only service products.",
                }
            }
        if flow == "device":
            is_diag_service = (
                self.product_id.type == "service"
                or getattr(self.product_id.product_tmpl_id, "item_type", False) == "diagnostic_service"
            )
            if is_diag_service:
                self.product_id = False
                return {
                    "warning": {
                        "title": "Invalid Product",
                        "message": "Device/HA flow does not allow diagnostic service products.",
                    }
                }

    def _get_product_hsn_sac_code(self):
        self.ensure_one()
        product = self.product_id
        if not product:
            return ""
        for field_name in ("l10n_in_hsn_code", "hs_code", "hs_code_id"):
            if hasattr(product, field_name):
                value = getattr(product, field_name)
                if not value and product.product_tmpl_id:
                    value = getattr(product.product_tmpl_id, field_name, False)
                if value:
                    raw = value.name if hasattr(value, "name") else value
                    return self._normalize_hsn_sac(raw)
        return ""

    def _apply_fixed_tax_from_matrix(self):
        for line in self:
            if line.display_type or not line.product_id:
                continue
            rate, prefer_exempt = line._get_fixed_gst_rate_from_client_matrix()
            if rate is None:
                continue
            taxes = line._find_sale_taxes_by_rate(rate, prefer_exempt=prefer_exempt)
            if not taxes:
                if (rate or 0.0) == 0.0 or prefer_exempt:
                    raise ValidationError(
                        f"GST Matrix mapped 0% Exempt for HSN/SAC "
                        f"'{line._get_product_hsn_sac_code()}', but no active sale tax "
                        "named Exempt/Nil/0% is configured. Please create a 0% Exempt sale tax."
                    )
                raise ValidationError(
                    f"GST Matrix mapped {rate:.2f}% for HSN/SAC "
                    f"'{line._get_product_hsn_sac_code()}', but matching sale taxes are not configured. "
                    "Please configure CGST+SGST (intra-state) and IGST (inter-state) taxes."
                )
            # Fixed-tax mode: do not allow fiscal-position remapping to alter matrix rate.
            line.tax_id = taxes

    def _get_fixed_gst_rate_from_client_matrix(self):
        """Resolve GST from GST Rate Matrix master by HSN/SAC."""
        self.ensure_one()
        code = self._get_product_hsn_sac_code()
        if not code:
            return None, False

        company = self.company_id or self.order_id.company_id or self.env.company
        supply_type = (
            "services"
            if getattr(self.product_id, "type", "") == "service"
            else "goods"
        )
        matrix_model = self.env["resonnocare.gst.rate.matrix"]
        matrix = matrix_model.search(
            [
                ("active", "=", True),
                ("hsn_sac_code", "=", code),
                ("company_id", "=", company.id),
                ("supply_type", "=", supply_type),
            ],
            limit=1,
        )
        if not matrix:
            matrix = matrix_model.search(
                [
                    ("active", "=", True),
                    ("hsn_sac_code", "=", code),
                    ("company_id", "=", company.id),
                ],
                limit=1,
            )
        if not matrix:
            matrix = matrix_model.search(
                [
                    ("active", "=", True),
                    ("hsn_sac_code", "=", code),
                    ("supply_type", "=", supply_type),
                ],
                limit=1,
            )
        if not matrix:
            matrix = matrix_model.search(
                [
                    ("active", "=", True),
                    ("hsn_sac_code", "=", code),
                ],
                limit=1,
            )
        if matrix:
            return matrix.gst_rate, bool(matrix.is_exempt)

        # Safety fallback to avoid accidental regression when master row is missing.
        if code in {"90214090", "999316"}:
            return 0.0, True
        if code in {"90219010", "998729", "85068010"}:
            return 18.0, False
        return None, False

    def _tax_effective_rate(self, tax):
        self.ensure_one()
        if tax.amount_type == "group":
            return sum(tax.children_tax_ids.filtered(lambda c: c.active).mapped("amount"))
        return tax.amount or 0.0

    def _is_inter_state_supply(self):
        self.ensure_one()
        company = self.company_id or self.order_id.company_id or self.env.company
        company_state = company.state_id
        partner = (
            self.order_id.partner_shipping_id
            or self.order_id.partner_invoice_id
            or self.order_id.partner_id
        )
        partner_state = partner.state_id if partner else False
        if not company_state or not partner_state:
            return False
        return company_state.id != partner_state.id

    def _find_sale_taxes_by_rate(self, rate, prefer_exempt=False):
        self.ensure_one()
        company = self.company_id or self.order_id.company_id or self.env.company
        taxes = self.env["account.tax"].search(
            [
                ("type_tax_use", "=", "sale"),
                ("company_id", "=", company.id),
                ("active", "=", True),
            ]
        )
        if not taxes:
            return self.env["account.tax"]

        no_price_include = taxes.filtered(lambda t: not t.price_include)
        taxes = no_price_include or taxes

        taxes = taxes.filtered(lambda t: abs((self._tax_effective_rate(t) or 0.0) - (rate or 0.0)) < 0.0001)
        if not taxes:
            return self.env["account.tax"]

        if prefer_exempt:
            exempt = taxes.filtered(
                lambda t: "EXEMPT" in (t.name or "").upper()
                or "NIL" in (t.name or "").upper()
                or "0%" in (t.name or "").upper()
            )
            if exempt:
                return exempt[:1]

        is_inter_state = self._is_inter_state_supply()
        if is_inter_state:
            # Prefer direct IGST % tax.
            igst = taxes.filtered(lambda t: "IGST" in (t.name or "").upper())
            if igst:
                return igst[:1]
            # Fallback: any exact-rate tax if IGST naming not present.
            return taxes[:1]
        else:
            # Prefer explicit CGST + SGST pair (common India setup).
            half_rate = (rate or 0.0) / 2.0
            base_taxes = self.env["account.tax"].search(
                [
                    ("type_tax_use", "=", "sale"),
                    ("company_id", "=", company.id),
                    ("active", "=", True),
                    ("amount_type", "=", "percent"),
                    ("price_include", "=", False),
                ]
            )
            cgst = base_taxes.filtered(
                lambda t: "CGST" in (t.name or "").upper()
                and abs((t.amount or 0.0) - half_rate) < 0.0001
            )[:1]
            sgst = base_taxes.filtered(
                lambda t: ("SGST" in (t.name or "").upper() or "UTGST" in (t.name or "").upper())
                and abs((t.amount or 0.0) - half_rate) < 0.0001
            )[:1]
            pair = cgst | sgst
            if pair:
                return pair

            # Next prefer grouped GST tax if configured.
            grouped = taxes.filtered(
                lambda t: t.amount_type == "group"
                and "GST" in (t.name or "").upper()
                and "IGST" not in (t.name or "").upper()
            )
            if grouped:
                return grouped[:1]
            # Final fallback: any exact-rate tax.
            return taxes[:1]

        gst_named = taxes.filtered(lambda t: "GST" in (t.name or "").upper())
        return (gst_named or taxes)[:1]

    @api.depends(
        "product_id",
        "product_uom",
        "product_uom_qty",
        "company_id",
        "order_id.partner_shipping_id",
        "order_id.partner_id",
        "order_id.fiscal_position_id",
    )
    def _compute_tax_id(self):
        super()._compute_tax_id()
        self._apply_fixed_tax_from_matrix()

    @api.onchange("product_id", "order_id.partner_shipping_id", "order_id.fiscal_position_id")
    def _onchange_force_tax_from_matrix(self):
        self._apply_fixed_tax_from_matrix()

    def _get_discount_channel(self):
        self.ensure_one()
        clinic = self.order_id.clinic_id or self.order_id.patient_id.clinic_id
        billing_type = (
            clinic._get_effective_billing_type() if clinic and hasattr(clinic, "_get_effective_billing_type") else "b2c"
        )

        # Updated rule: discount channel is clinic-driven (not patient expense-driven).
        # B2B clinic billing => H/SIS
        # B2C / COCO clinic billing => Corporate
        if billing_type == "b2b":
            return "hsis"
        if billing_type == "b2c":
            return "corporate"
        return "hsis"

    @api.depends(
        "order_id.clinic_id",
        "order_id.clinic_id.clinic_type",
        "order_id.clinic_id.clinic_subtype",
        "order_id.patient_id",
        "order_id.patient_id.clinic_id",
        "order_id.patient_id.clinic_id.clinic_type",
        "order_id.patient_id.clinic_id.clinic_subtype",
        "product_id",
        "price_unit",
        "discount",
    )
    def _compute_discount_grid_meta(self):
        Grid = self.env["resonnocare.discount.grid"]
        Diag = self.env["resonnocare.diagnostic.item"]
        ClinicDiag = self.env["resonnocare.clinic.diagnostic"]
        for line in self:
            if not line.product_id:
                line.discount_channel = False
                line.discount_grid_id = False
                line.discount_base_mrp = 0.0
                line.discount_reference_mrp = 0.0
                continue

            channel = line._get_discount_channel()
            ptype = getattr(line.product_id, "type", False)
            clinic = line.order_id.clinic_id or line.order_id.patient_id.clinic_id

            if ptype == "service":
                mrp = 0.0
                if clinic:
                    diag = Diag.search([("product_id", "=", line.product_id.id)], limit=1)
                    if diag:
                        clinic_diag = ClinicDiag.search(
                            [
                                ("clinic_id", "=", clinic.id),
                                ("diagnostic_item_id", "=", diag.id),
                            ],
                            limit=1,
                        )
                        mrp = clinic_diag.mrp or 0.0
            else:
                mrp = line.product_id.lst_price or 0.0

            grid = Grid.search(
                [
                    ("active", "=", True),
                    ("channel", "=", channel),
                    ("mrp_from", "<=", mrp),
                    "|",
                    ("mrp_to", "=", 0),
                    ("mrp_to", ">=", mrp),
                ],
                order="mrp_from desc, id desc",
                limit=1,
            )
            line.discount_channel = channel
            line.discount_grid_id = grid.id if grid else False
            # Keep reference MRP for internal metrics/approval logic.
            line.discount_reference_mrp = mrp
            # Display discount value in currency (how much amount is reduced).
            discount_value = (mrp * (line.product_uom_qty or 0.0)) * (
                (line.discount or 0.0) / 100.0
            )
            line.discount_base_mrp = discount_value

    @api.depends("discount", "discount_grid_id")
    def _compute_discount_slab(self):
        for line in self:
            grid = line.discount_grid_id
            if not grid:
                line.discount_slab = False
                continue
            if line.discount <= grid.slab1_max:
                line.discount_slab = "slab1"
            elif line.discount <= grid.slab2_max:
                line.discount_slab = "slab2"
            else:
                line.discount_slab = "slab3"

    @api.constrains("discount", "discount_grid_id", "product_id")
    def _check_discount_grid_presence(self):
        for line in self:
            if not line.product_id:
                continue
            if not line.discount_grid_id:
                raise ValidationError(
                    "No Discount Grid rule matched for this line. "
                    "For services, configure clinic-level diagnostic MRP; "
                    "for devices, verify product MRP and Discount Grid bands."
                )

    def _prepare_base_line_for_taxes_computation(self, **kwargs):
        if self.discount_type == "fixed" and self.discount_fixed:
            kwargs["price_unit"] = self.price_unit - self.discount_fixed
            kwargs["discount"] = 0.0
        return super()._prepare_base_line_for_taxes_computation(**kwargs)

    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)
        if self.discount_type == "fixed" and self.discount_fixed:
            res["price_unit"] = self.price_unit - self.discount_fixed
            res["discount"] = 0.0
        return res
