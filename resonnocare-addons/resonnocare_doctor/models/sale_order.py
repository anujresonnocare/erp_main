from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    referring_doctor_id = fields.Many2one(
        "resonnocare.doctor.profile",
        string="Referring Doctor",
        index=True,
    )
    net_ha_sale_value = fields.Monetary(
        string="Net HA Sale Value",
        currency_field="currency_id",
        compute="_compute_doctor_commission",
        store=True,
    )
    net_diagnostic_revenue = fields.Monetary(
        string="Net Diagnostic Revenue",
        currency_field="currency_id",
        compute="_compute_doctor_commission",
        store=True,
    )
    doctor_commission_amount = fields.Monetary(
        string="Doctor Commission",
        currency_field="currency_id",
        compute="_compute_doctor_commission",
        store=True,
    )
    show_net_ha_sale_value = fields.Boolean(
        string="Show Net HA Sale Value",
        compute="_compute_sale_flow_visibility",
        store=False,
    )
    show_net_diagnostic_revenue = fields.Boolean(
        string="Show Net Diagnostic Revenue",
        compute="_compute_sale_flow_visibility",
        store=False,
    )

    def _register_hook(self):
        result = super()._register_hook()
        rule_model = self.env["ir.rule"].sudo()

        # Ensure doctor rule always includes both explicit SO doctor field and
        # fallback via patient mapping.
        doctor_rule = self.env.ref(
            "resonnocare_doctor.sale_order_rule_external_doctor",
            raise_if_not_found=False,
        )
        doctor_domain = (
            "["
            " '|',"
            " ('referring_doctor_id', '=', user.external_doctor_profile_id.id),"
            " '|',"
            " '&', ('patient_id', '!=', False), ('patient_id.referring_doctor_id', '=', user.external_doctor_profile_id.id),"
            " '&', ('partner_id.is_patient', '=', True), ('partner_id.referring_doctor_id', '=', user.external_doctor_profile_id.id)"
            "]"
        )
        if doctor_rule and doctor_rule.domain_force != doctor_domain:
            doctor_rule.write({"domain_force": doctor_domain})

        # A global clinic scope rule can hide all sales for external doctors
        # because they don't have clinic_id. Allow external-doctor sales through
        # doctor linkage while keeping clinic scope for internal users.
        clinic_scope_rules = rule_model.search(
            [
                ("model_id.model", "=", "sale.order"),
                ("name", "=", "Sale Orders: Clinic Scope (Global)"),
                ("global", "=", True),
            ]
        )
        clinic_scope_domain = (
            "["
            " '|',"
            " ('clinic_id', '=', user.clinic_id.id),"
            " ('referring_doctor_id.user_id', '=', user.id)"
            "]"
        )
        if clinic_scope_rules:
            clinic_scope_rules.write({"domain_force": clinic_scope_domain})
        return result

    @api.depends(
        "order_line.price_subtotal",
        "order_line.product_id",
        "order_line.doctor_sharing_amount",
        "patient_id.referring_doctor_id",
        "patient_id.referral_source",
        "partner_id.referring_doctor_id",
        "referring_doctor_id",
        "referring_doctor_id.commission_ha_percent",
        "referring_doctor_id.commission_diagnostic_percent",
    )
    def _compute_doctor_commission(self):
        for order in self:
            doctor = order.referring_doctor_id or order._get_doctor_from_patient()
            ha_total = 0.0
            diagnostic_total = 0.0
            for line in order.order_line:
                if line.display_type:
                    continue
                if line.product_id and line.product_id.type == "service":
                    diagnostic_total += line.price_subtotal
                else:
                    ha_total += line.price_subtotal
            order.net_ha_sale_value = ha_total
            order.net_diagnostic_revenue = diagnostic_total
            if doctor:
                computed = sum(order.order_line.mapped("doctor_sharing_amount"))
                has_rule_based_line = any(
                    bool(rule_id)
                    for rule_id in order.order_line.mapped("doctor_sharing_rule_id")
                )
                # Fallback to legacy commission % only when no sharing rule matched.
                if not has_rule_based_line:
                    computed = (
                        (ha_total * (doctor.commission_ha_percent or 0.0) / 100.0)
                        + (
                            diagnostic_total
                            * (doctor.commission_diagnostic_percent or 0.0)
                            / 100.0
                        )
                    )
                order.doctor_commission_amount = computed
            else:
                order.doctor_commission_amount = 0.0

    @api.depends(
        "order_line",
        "order_line.product_id",
        "order_line.product_id.type",
        "order_line.display_type",
        "invoice_ids",
        "invoice_ids.state",
    )
    def _compute_sale_flow_visibility(self):
        for order in self:
            # Primary rule from SO lines (most reliable for UI visibility).
            lines = order.order_line.filtered(lambda l: l.product_id and not l.display_type)
            has_device = any(l.product_id.type in ("product", "consu") for l in lines)
            has_service = any(l.product_id.type == "service" for l in lines)

            if has_device:
                flow = "device"
            elif has_service:
                flow = "service"
            else:
                # Fallback to appointment-derived flow when there are no product lines yet.
                flow = order._get_sale_flow_type() if hasattr(order, "_get_sale_flow_type") else False

            order.show_net_ha_sale_value = flow == "device"
            order.show_net_diagnostic_revenue = flow == "service"

    def _get_doctor_from_patient(self):
        self.ensure_one()
        patient = self.patient_id
        if not patient and self.partner_id and self.partner_id.is_patient:
            patient = self.partner_id
        return patient.referring_doctor_id if patient else False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("referring_doctor_id") and vals.get("patient_id"):
                patient = self.env["res.partner"].browse(vals["patient_id"])
                if patient and patient.referring_doctor_id:
                    vals["referring_doctor_id"] = patient.referring_doctor_id.id
            if not vals.get("referring_doctor_id") and vals.get("partner_id"):
                partner = self.env["res.partner"].browse(vals["partner_id"])
                if partner and partner.is_patient and partner.referring_doctor_id:
                    vals["referring_doctor_id"] = partner.referring_doctor_id.id
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if any(k in vals for k in ("patient_id", "partner_id", "referring_doctor_id")):
            for order in self:
                if not order.referring_doctor_id:
                    doctor = order._get_doctor_from_patient()
                    if doctor:
                        order.referring_doctor_id = doctor.id
        return res

    @api.onchange("patient_id")
    def _onchange_patient_doctor(self):
        if self.patient_id and self.patient_id.is_patient:
            self.referring_doctor_id = self.patient_id.referring_doctor_id

    def action_confirm(self):
        for order in self:
            if not order.referring_doctor_id:
                doctor = order._get_doctor_from_patient()
                if doctor:
                    order.referring_doctor_id = doctor.id
        return super().action_confirm()


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    discount_type = fields.Selection(
            selection=[
                ('sol_discount', "On All Order Lines"),
                ('so_discount', "Global Discount"),
                ('amount', "Fixed Amount"),
            ],
            default='sol_discount',
        )

    clinic_sharing_pct = fields.Float(
        string="Clinic Sharing %",
        compute="_compute_sharing_values",
        store=True,
    )
    clinic_sharing_amount = fields.Monetary(
        string="Clinic Sharing Amount",
        currency_field="currency_id",
        compute="_compute_sharing_values",
        store=True,
    )
    clinic_sharing_rule_id = fields.Many2one(
        "resonnocare.clinic.sharing.rule",
        string="Clinic Sharing Rule",
        compute="_compute_sharing_values",
        store=True,
    )
    doctor_sharing_pct = fields.Float(
        string="Doctor Sharing %",
        compute="_compute_sharing_values",
        store=True,
    )
    doctor_sharing_amount = fields.Monetary(
        string="Doctor Sharing Amount",
        currency_field="currency_id",
        compute="_compute_sharing_values",
        store=True,
    )
    doctor_sharing_rule_id = fields.Many2one(
        "resonnocare.doctor.sharing.rule",
        string="Doctor Sharing Rule",
        compute="_compute_sharing_values",
        store=True,
    )

    @api.depends(
        "order_id.clinic_id",
        "order_id.patient_id",
        "order_id.patient_id.clinic_id",
        "order_id.patient_id.referral_source",
        "order_id.referring_doctor_id",
        "product_id",
        "price_unit",
        "price_subtotal",
    )
    def _compute_sharing_values(self):
        for line in self:
            line.clinic_sharing_pct = 0.0
            line.clinic_sharing_amount = 0.0
            line.clinic_sharing_rule_id = False
            line.doctor_sharing_pct = 0.0
            line.doctor_sharing_amount = 0.0
            line.doctor_sharing_rule_id = False
            if line.display_type or not line.product_id:
                continue

            order = line.order_id
            clinic = order.clinic_id or order.patient_id.clinic_id
            source_category = order.patient_id.referral_source or False
            if not clinic:
                continue

            clinic_sharing = clinic._resolve_clinic_sharing(
                product=line.product_id,
                mrp=(line.price_unit or 0.0),
                source_category=source_category,
            )
            clinic_pct = clinic_sharing.get("sharing_percent", 0.0) or 0.0
            line.clinic_sharing_pct = clinic_pct
            line.clinic_sharing_amount = (line.price_subtotal or 0.0) * clinic_pct / 100.0
            line.clinic_sharing_rule_id = clinic_sharing.get("rule_id") or False

            doctor = order.referring_doctor_id or order._get_doctor_from_patient()
            if not doctor:
                continue
            doctor_sharing = doctor._resolve_doctor_sharing(
                clinic=clinic,
                product=line.product_id,
                mrp=(line.price_unit or 0.0),
                source_category=source_category,
            )
            doctor_rule_id = doctor_sharing.get("rule_id") or False
            doctor_pct = doctor_sharing.get("sharing_percent", 0.0) or 0.0
            # Fallback only when no doctor-sharing rule matched.
            if not doctor_rule_id:
                # Legacy fallback.
                if line.product_id.type == "service":
                    doctor_pct = doctor.commission_diagnostic_percent or 0.0
                else:
                    doctor_pct = doctor.commission_ha_percent or 0.0
            line.doctor_sharing_pct = doctor_pct
            line.doctor_sharing_amount = (line.price_subtotal or 0.0) * doctor_pct / 100.0
            line.doctor_sharing_rule_id = doctor_rule_id
