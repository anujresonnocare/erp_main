# -*- coding: utf-8 -*-
from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, time, timedelta
from collections import defaultdict
import pytz

import logging

logger = logging.getLogger(__name__)


def _build_time_slot_selection():
    slots = []
    for total_minutes in range(0, 24 * 60, 5):
        hour_24 = total_minutes // 60
        minute = total_minutes % 60
        meridiem = "AM" if hour_24 < 12 else "PM"
        hour_12 = hour_24 % 12 or 12
        slots.append((f"{hour_24:02d}:{minute:02d}", f"{hour_12:02d}:{minute:02d} {meridiem}"))
    return slots


class ResonnocareAppointment(models.Model):
    _name = "resonnocare.appointment"
    _description = "Clinic Appointment"
    _order = "appointment_date, appointment_start_time, id"
    _rec_name = "name"
    _rec_name = "name"
    _TIME_SLOT_SELECTION = _build_time_slot_selection()

    appointment_id = fields.Char(string="Appointment ID", readonly=True, copy=False)
    name = fields.Char(string="Title", compute="_compute_name", store=True)
    name = fields.Char(string="Title", compute="_compute_name", store=True)

    clinic_id = fields.Many2one(
        "resonnocare.clinic",
        string="Clinic",
        required=True,
        compute="_compute_clinic_id",
        store=True,
        readonly=False,
        precompute=True,
    )

    patient_id = fields.Many2one(
        "res.partner",
        string="Patient",
        required=True,
        domain=[("is_patient", "=", True)],
    )

    appointment_type_id = fields.Many2one(
        "resonnocare.appointment.type", string="Appointment Type", required=True
    )

    appointment_date = fields.Date(string="Appointment Date", required=True)

    appointment_start_time = fields.Float(string="Start Time", required=True)
    appointment_start_slot = fields.Selection(
        selection=_TIME_SLOT_SELECTION,
        string="Start Time",
        compute="_compute_start_slot",
        inverse="_inverse_start_slot",
    )

    appointment_end_time = fields.Float(
        string="End Time", compute="_compute_end_time", store=True
    )

    appointment_start_datetime = fields.Datetime(
        string="Start (Calendar)",
        compute="_compute_start_end_datetime",
        store=True,
    )

    appointment_end_datetime = fields.Datetime(
        string="End (Calendar)",
        compute="_compute_start_end_datetime",
        store=True,
    )

    doctor_name = fields.Char(
        string="Referal Doctor",
        compute="_compute_referral_doctor_name",
        store=True,
        readonly=True,
    )

    audiologist_id = fields.Many2one(
        "hr.employee",
        string="Audiologist",
        domain="[('clinic_role','=','doctor')]",
    )
    technician_id = fields.Many2one(
        "hr.employee",
        string="Technician",
        domain="[('clinic_role','=','technician')]",
    )

    available_audiologist_ids = fields.Many2many(
        "hr.employee",
        string="Available Audiologists",
        compute="_compute_available_audiologists",
        store=False,
    )
    available_technician_ids = fields.Many2many(
        "hr.employee",
        string="Available Technicians",
        compute="_compute_available_technicians",
        store=False,
    )


    diagnostic_item_ids = fields.Many2many(
        "resonnocare.diagnostic.item", string="Diagnostic Tests"
    )
    appointment_outcome_ids = fields.Many2many(
        "resonnocare.appointment.outcome",
        "resonnocare_appointment_outcome_rel",
        "appointment_id",
        "outcome_id",
        string="Appointment Outcomes",
    )

    device_sale_line_ids = fields.One2many(
        "resonnocare.appointment.device.line",
        "appointment_id",
        string="Device Sale Lines",
    )

    sale_type = fields.Selection(
        [
            ("service", "Service"),
            ("device", "Device"),
        ],
        string="Sale Type",
        default="service",
    )
    is_diagnostic_service_type = fields.Boolean(
        string="Diagnostic/Service Type",
        compute="_compute_is_diagnostic_service_type",
        store=False,
    )
    is_device_goods_type = fields.Boolean(
        string="Device/Goods Type",
        compute="_compute_is_device_goods_type",
        store=False,
    )

    pre_booking = fields.Boolean(string="Pre-Booking")
    expected_delivery_date = fields.Date(string="Expected Delivery Date")

    parent_appointment_id = fields.Many2one(
        "resonnocare.appointment",
        string="Original Appointment",
        ondelete="set null",
    )

    fitting_appointment_ids = fields.One2many(
        "resonnocare.appointment",
        "parent_appointment_id",
        string="Fitting Appointments",
    )

    fitting_device_line_ids = fields.One2many(
        "resonnocare.appointment.device.line",
        related="parent_appointment_id.device_sale_line_ids",
        string="Fitting Devices",
        readonly=True,
    )

    appointment_role = fields.Selection(
        [
            ("original", "Original"),
            ("fitting", "Fitting"),
        ],
        string="Appointment Role",
        compute="_compute_appointment_role",
        store=True,
        readonly=True,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="clinic_id.company_id.currency_id",
        readonly=True,
    )

    balance_due = fields.Monetary(
        string="Balance Due",
        compute="_compute_balance_due",
        currency_field="currency_id",
        store=False,
    )
    can_request_min_advance = fields.Boolean(
        string="Can Request Min Advance",
        compute="_compute_can_request_min_advance",
        store=False,
    )

    notes = fields.Text(string="Notes")

    source = fields.Selection(
        [
            ("crm", "CRM"),
            ("walkin", "Walk-in"),
            ("referral", "Doctor Referral"),
        ],
        string="Source",
        default="walkin",
    )

    status = fields.Selection(
        [
            ("draft", "Draft"),
            ("scheduled", "Scheduled"),
            ("checked_in", "Checked In"),
            ("in_consultation", "In Consultation"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
            ("no_show", "No Show"),
        ],
        default="draft",
        required=True,
    )
    can_edit_clinic = fields.Boolean(
        string="Can Edit Clinic",
        compute="_compute_can_edit_clinic",
    )

    color_index = fields.Integer(
        string="Color Index",
        compute="_compute_color_index",
        store=True,
    )

    sale_order_id = fields.Many2one(
    "sale.order",
    string="Sale Order",
    readonly=True,
    copy=False,
    )

    is_billed = fields.Boolean(
        string="Billed",
        compute="_compute_is_billed",
        store=False,
    )

    def _compute_is_billed(self):
        for rec in self:
            rec.is_billed = bool(rec.sale_order_id)

    @api.depends("appointment_start_time")
    def _compute_start_slot(self):
        for rec in self:
            if rec.appointment_start_time is False:
                rec.appointment_start_slot = False
                continue
            total_minutes = int(round((rec.appointment_start_time or 0.0) * 60))
            rounded_minutes = int(round(total_minutes / 5.0) * 5) % (24 * 60)
            hour_24 = rounded_minutes // 60
            minute = rounded_minutes % 60
            rec.appointment_start_slot = f"{hour_24:02d}:{minute:02d}"

    def _compose_start_time_from_slot(self):
        self.ensure_one()
        if not self.appointment_start_slot:
            return False
        try:
            hour_raw, minute_raw = self.appointment_start_slot.split(":")
            hour_24 = int(hour_raw)
            minute = int(minute_raw)
        except Exception as exc:
            raise ValidationError(_("Invalid start time selection.")) from exc
        return hour_24 + (minute / 60.0)

    def _inverse_start_slot(self):
        for rec in self:
            composed = rec._compose_start_time_from_slot()
            if composed is not False:
                rec.appointment_start_time = composed

    @api.onchange("appointment_start_slot")
    def _onchange_start_slot(self):
        for rec in self:
            composed = rec._compose_start_time_from_slot()
            if composed is not False:
                rec.appointment_start_time = composed

    @api.depends('parent_appointment_id')
    def _compute_appointment_role(self):
        for rec in self:
            if rec.parent_appointment_id:
                rec.appointment_role = "fitting"
            else:
                rec.appointment_role = "original"

    @api.depends(
        "sale_order_id",
        "sale_order_id.amount_total",
        "sale_order_id.amount_invoiced",
        "sale_order_id.amount_to_invoice",
        "sale_order_id.invoice_ids.state",
        "sale_order_id.invoice_ids.amount_total",
        "sale_order_id.invoice_ids.amount_residual",
    )
    def _compute_balance_due(self):
        for rec in self:
            sale = rec._get_effective_sale_order()
            if not sale:
                rec.balance_due = 0.0
                continue

            customer_invoices = rec._get_related_customer_invoices(sale)
            posted_invoices = customer_invoices.filtered(lambda inv: inv.state == "posted")
            total_paid = sum(inv._get_contract_advance_paid() for inv in posted_invoices)
            balance = (sale.amount_total or 0.0) - total_paid
            if balance < 0:
                balance = 0.0
            rec.balance_due = balance

    @api.depends(
        "sale_order_id",
        "sale_order_id.amount_total",
        "sale_order_id.invoice_ids.state",
        "sale_order_id.invoice_ids.amount_total",
        "sale_order_id.invoice_ids.amount_residual",
        "parent_appointment_id",
        "parent_appointment_id.sale_order_id",
        "parent_appointment_id.sale_order_id.amount_total",
        "parent_appointment_id.sale_order_id.invoice_ids.state",
        "parent_appointment_id.sale_order_id.invoice_ids.amount_total",
        "parent_appointment_id.sale_order_id.invoice_ids.amount_residual",
        "sale_type",
        "status",
    )
    def _compute_can_request_min_advance(self):
        for rec in self:
            rec.can_request_min_advance = False
            if rec.sale_type != "device" or rec.parent_appointment_id:
                continue
            sale = rec._get_effective_sale_order()
            if not sale:
                continue
            minimum_required = (sale.amount_total or 0.0) * 0.30
            total_paid = rec._get_total_paid_for_sale(sale)
            rec.can_request_min_advance = bool(total_paid < minimum_required)

    def _get_effective_sale_order(self):
        self.ensure_one()
        if self.parent_appointment_id and self.parent_appointment_id.sale_order_id:
            return self.parent_appointment_id.sale_order_id
        return self.sale_order_id

    def _get_related_customer_invoices(self, sale):
        self.ensure_one()
        sale_sudo = sale.sudo()
        invoices = sale_sudo.invoice_ids.filtered(
            lambda inv: inv.move_type == "out_invoice" and inv.state != "cancel"
        )
        invoices |= sale_sudo.order_line.mapped("invoice_lines.move_id").filtered(
            lambda inv: inv.move_type == "out_invoice" and inv.state != "cancel"
        )
        invoice_model = self.env["account.move"].sudo()
        invoices |= invoice_model.search(
            [
                ("move_type", "=", "out_invoice"),
                ("state", "!=", "cancel"),
                ("invoice_line_ids.sale_line_ids.order_id", "=", sale_sudo.id),
            ]
        )
        if sale_sudo.name:
            invoices |= invoice_model.search(
                [
                    ("move_type", "=", "out_invoice"),
                    ("state", "!=", "cancel"),
                    ("invoice_origin", "=", sale_sudo.name),
                ]
            )
            invoices |= invoice_model.search(
                [
                    ("move_type", "=", "out_invoice"),
                    ("state", "!=", "cancel"),
                    ("invoice_origin", "ilike", sale_sudo.name),
                ]
            )
        origin_refs = [ref for ref in [sale_sudo.origin, self.appointment_id] if ref]
        if self.parent_appointment_id and self.parent_appointment_id.appointment_id:
            origin_refs.append(self.parent_appointment_id.appointment_id)
        for ref in set(origin_refs):
            invoices |= invoice_model.search(
                [
                    ("move_type", "=", "out_invoice"),
                    ("state", "!=", "cancel"),
                    ("invoice_origin", "=", ref),
                ]
            )
            invoices |= invoice_model.search(
                [
                    ("move_type", "=", "out_invoice"),
                    ("state", "!=", "cancel"),
                    ("invoice_origin", "ilike", ref),
                ]
            )
        return invoices

    def _get_total_paid_for_sale(self, sale):
        self.ensure_one()
        invoices = self._get_related_customer_invoices(sale).filtered(
            lambda inv: inv.state == "posted"
        )
        logger.info(
            "Calculating total paid for sale 77777777777777777777777%s: Found %d related posted invoices.",
            sale.name,
            len(invoices),
        )
        total_paid = sum(inv._get_contract_advance_paid() for inv in invoices)
        logger.info(
            "Total paid for sale 6666666666666666666666666%s: %f",
            sale.name,
            total_paid
        )
        return total_paid

    @api.depends("audiologist_id", "patient_id")
    def _compute_name(self):
        for rec in self:
            if rec.audiologist_id:
                rec.name = rec.audiologist_id.name
            elif rec.patient_id:
                rec.name = rec.patient_id.name
            else:
                rec.name = "Appointment"

    @api.depends("patient_id", "patient_id.referring_doctor")
    def _compute_referral_doctor_name(self):
        for rec in self:
            if rec.patient_id and rec.patient_id.referring_doctor:
                rec.doctor_name = rec.patient_id.referring_doctor
            else:
                rec.doctor_name = False

    @api.depends("audiologist_id", "patient_id")
    def _compute_name(self):
        for rec in self:
            if rec.audiologist_id:
                rec.name = rec.audiologist_id.name
            elif rec.patient_id:
                rec.name = rec.patient_id.name
            else:
                rec.name = "Appointment"

    def _get_source_from_patient(self, patient):
        if not patient:
            return False
        mapping = {
            "crm": "crm",
            "walkin": "walkin",
            "doctor": "referral",
        }
        return mapping.get(patient.referral_source, False)

    @api.depends("patient_id")
    def _compute_clinic_id(self):
        user_clinic = self.env.user.clinic_id or self.env.user.employee_id.clinic_id
        for rec in self:
            if rec.patient_id and rec.patient_id.clinic_id:
                rec.clinic_id = rec.patient_id.clinic_id
            elif not rec.clinic_id:
                rec.clinic_id = user_clinic

    @api.onchange("patient_id")
    def _onchange_patient_source(self):
        for rec in self:
            if rec.patient_id:
                mapped = rec._get_source_from_patient(rec.patient_id)
                if mapped:
                    rec.source = mapped
                if rec.patient_id.clinic_id:
                    rec.clinic_id = rec.patient_id.clinic_id

    @api.onchange("sale_type")
    def _onchange_sale_type(self):
        for rec in self:
            if rec.sale_type == "service":
                rec.device_sale_line_ids = [(5, 0, 0)]
                rec.pre_booking = False
                rec.expected_delivery_date = False
            elif rec.sale_type == "device":
                rec.diagnostic_item_ids = [(5, 0, 0)]

    @api.depends("appointment_type_id", "appointment_type_id.sale_type", "appointment_type_id.name")
    def _compute_is_diagnostic_service_type(self):
        for rec in self:
            if rec.appointment_type_id and rec.appointment_type_id.sale_type:
                rec.is_diagnostic_service_type = rec.appointment_type_id.sale_type == "service"
                continue
            name = (rec.appointment_type_id.name or "").strip().lower()
            rec.is_diagnostic_service_type = bool(
                name and ("diagnostic" in name or "service" in name)
            )

    @api.depends("appointment_type_id", "appointment_type_id.sale_type", "appointment_type_id.name")
    def _compute_is_device_goods_type(self):
        for rec in self:
            if rec.appointment_type_id and rec.appointment_type_id.sale_type:
                rec.is_device_goods_type = rec.appointment_type_id.sale_type == "device"
                continue
            name = (rec.appointment_type_id.name or "").strip().lower()
            rec.is_device_goods_type = bool(
                name
                and any(
                    token in name
                    for token in ("device", "goods", "hearing", "trial", "fitting")
                )
                and not ("diagnostic" in name or "service" in name)
            )

    @api.onchange("appointment_type_id")
    def _onchange_appointment_type_force_service(self):
        for rec in self:
            if rec.appointment_type_id and rec.appointment_type_id.sale_type:
                rec.sale_type = rec.appointment_type_id.sale_type
                continue
            if rec.is_diagnostic_service_type and rec.sale_type != "service":
                rec.sale_type = "service"
            elif rec.is_device_goods_type and rec.sale_type != "device":
                rec.sale_type = "device"

    @api.onchange("diagnostic_item_ids")
    def _onchange_diagnostic_items_set_sale_type(self):
        for rec in self:
            if rec.diagnostic_item_ids and rec.sale_type != "service":
                rec.sale_type = "service"

    @api.onchange("device_sale_line_ids")
    def _onchange_device_lines_set_sale_type(self):
        for rec in self:
            if rec.device_sale_line_ids and rec.sale_type != "device":
                rec.sale_type = "device"

    def _get_sale_tax_ids_for_product(self, product, company):
        taxes = product.taxes_id.filtered(
            lambda t: not t.company_id or t.company_id == company
        )
        if taxes:
            return taxes.ids
        default_tax = getattr(company, "account_sale_tax_id", False)
        if default_tax:
            return [default_tax.id]
        return []

    def action_generate_bill(self):
        for rec in self:
            if rec.sale_order_id:
                raise UserError("Bill already generated for this appointment.")

            if not rec.appointment_id:
                raise UserError("Please confirm the appointment before billing.")

            if rec.status in ("cancelled", "no_show"):
                raise UserError("Cannot bill a cancelled or no-show appointment.")

            if not rec.patient_id:
                raise UserError("Please select a patient before billing.")

            if rec.device_sale_line_ids:
                raise UserError(
                    "Device sale already prepared for this appointment. "
                    "You can only bill services or devices, not both."
                )

            if not rec.diagnostic_item_ids:
                raise UserError("Please select diagnostic tests before billing.")

            if not rec.clinic_id or not rec.clinic_id.warehouse_id:
                raise UserError("Clinic warehouse is not configured.")

            clinic_pricing = self.env["resonnocare.clinic.diagnostic"].search(
                [
                    ("clinic_id", "=", rec.clinic_id.id),
                    ("diagnostic_item_id", "in", rec.diagnostic_item_ids.ids),
                ]
            )
            pricing_by_diag = {
                line.diagnostic_item_id.id: line.mrp for line in clinic_pricing
            }

            order_lines = []

            for test in rec.diagnostic_item_ids:
                if not test.product_id:
                    raise UserError(
                        f"Diagnostic test '{test.name}' is not linked to a service product."
                    )

                if test.id not in pricing_by_diag:
                    raise UserError(
                        f"MRP not configured for diagnostic '{test.name}' "
                        f"in clinic '{rec.clinic_id.name}'."
                    )

                order_lines.append(
                    (0, 0, {
                        "product_id": test.product_id.id,
                        "product_uom_qty": 1,
                        "price_unit": pricing_by_diag[test.id],
                        "name": test.product_id.name,
                    })
                )

            sale = self.env["sale.order"].create({
                "partner_id": rec.patient_id.id,
                "patient_id": rec.patient_id.id,
                "clinic_id": rec.clinic_id.id,
                "warehouse_id": rec.clinic_id.warehouse_id.id,
                "origin": rec.appointment_id,
                "order_line": order_lines,
            })
            # Force GST matrix taxes on auto-generated lines.
            sale.order_line._apply_fixed_tax_from_matrix()

            sale.action_confirm()
            rec.sale_order_id = sale.id

    def _apply_device_sale_picking_locations(self, sale, source_location):
        for picking in sale.picking_ids.filtered(
            lambda p: p.picking_type_code == "outgoing"
        ):
            picking.location_id = source_location.id
            for move in picking.move_ids_without_package:
                move.location_id = source_location.id
            for move_line in picking.move_line_ids:
                move_line.location_id = source_location.id

    def _get_available_qty_in_location(self, product, location):
        if not product or not location:
            return 0.0
        return self.env["stock.quant"]._get_available_quantity(
            product, location, strict=False
        )

    # def _create_ho_supply_request_for_device_booking(self):
    #     self.ensure_one()
    #     if not self.device_sale_line_ids:
    #         return False
        
    #     # ✅ CHECK: FULL PAYMENT OR MINIMUM ADVANCE APPROVED
    #     sale = self._get_effective_sale_order()
    #     if sale:
    #         total_order = (sale.amount_total or 0.0)
    #         total_paid = self._get_total_paid_for_sale(sale)
            
    #         # Supply order creates if:
    #         # 1. FULL payment (100%) is done, OR
    #         # 2. Minimum advance (30%) is APPROVED
    #         is_full_paid = total_paid >= total_order
            
    #         if not is_full_paid:
    #             # Check for approved minimum advance request
    #             approved_request = self.env["resonnocare.advance.approval.request"].search(
    #                 [
    #                     ("sale_order_id", "=", sale.id),
    #                     ("state", "=", "approved"),
    #                 ],
    #                 order="id desc",
    #                 limit=1,
    #             )
                
    #             # If no approved request, don't create supply order
    #             if not approved_request:
    #                 return False
        
    #     clinic = self.clinic_id
    #     company = clinic.company_id or self.env.company
    #     ho_warehouse = company.ho_warehouse_id
    #     source_location = company.ho_hearing_aid_sale_location_id or (
    #         ho_warehouse.lot_stock_id if ho_warehouse else False
    #     )
    #     destination_location = clinic.hearing_aid_sale_location_id or clinic.stock_location_id
    #     picking_type = ho_warehouse.int_type_id if ho_warehouse else False

    #     if not (ho_warehouse and source_location and destination_location and picking_type):
    #         return False

    #     # Requested qty:
    #     # - Pre-booking: full booked quantity goes to HO request.
    #     # - Normal flow: only clinic stock shortfall is requested.
    #     request_qty_by_product = defaultdict(float)
    #     available_cache = {}
    #     consumed_qty = defaultdict(float)

    #     for line in self.device_sale_line_ids:
    #         product = line.product_id
    #         if not product:
    #             continue
    #         ordered_qty = line.product_uom_qty or 0.0
    #         if ordered_qty <= 0:
    #             continue

    #         if self.pre_booking:
    #             req_qty = ordered_qty
    #         else:
    #             if product.id not in available_cache:
    #                 available_cache[product.id] = self._get_available_qty_in_location(
    #                     product, destination_location
    #                 )
    #             remaining = max(available_cache[product.id] - consumed_qty[product.id], 0.0)
    #             req_qty = max(ordered_qty - remaining, 0.0)
    #             consumed_qty[product.id] += ordered_qty

    #         if req_qty > 0:
    #             request_qty_by_product[product.id] += req_qty

    #     if not request_qty_by_product:
    #         return False

    #     move_vals = []
    #     for product_id, qty in request_qty_by_product.items():
    #         product = self.env["product.product"].browse(product_id)
    #         move_vals.append(
    #             (
    #                 0,
    #                 0,
    #                 {
    #                     "name": product.display_name,
    #                     "product_id": product.id,
    #                     "product_uom_qty": qty,
    #                     "product_uom": product.uom_id.id,
    #                     "location_id": source_location.id,
    #                     "location_dest_id": destination_location.id,
    #                     "company_id": company.id,
    #                 },
    #             )
    #         )

    #     supply_picking = self.env["stock.picking"].create(
    #         {
    #             "picking_type_id": picking_type.id,
    #             "location_id": source_location.id,
    #             "location_dest_id": destination_location.id,
    #             "origin": f"{self.appointment_id or self.display_name}",
    #             "company_id": company.id,
    #             "move_ids_without_package": move_vals,
    #         }
    #     )
    #     supply_picking.action_confirm()
    #     return supply_picking

    def _create_ho_supply_request_for_device_booking(self):
        self.ensure_one()
        
        # CHECK 1: Device lines exist
        if not self.device_sale_line_ids:
            raise UserError(
                "❌ SCM Order cannot be created: No device sale lines found.\n"
                "Please add at least one device to the appointment before generating SCM Order."
            )
        
        # CHECK 2: Sale order exists
        sale = self._get_effective_sale_order()
        if not sale:
            raise UserError(
                "❌ SCM Order cannot be created: No sale order linked to this appointment.\n"
                "Please generate device sale first by clicking 'Create SCM Order' button."
            )
        
        # CHECK 3: Payment/Advance requirement
        total_order = sale.amount_total or 0.0
        
        total_paid = self._get_total_paid_for_sale(sale)
        minimum_required = total_order * 0.30

        logger.info(
            "Checking payment for sale888888888888888888888 %s: Total Order = %f, Total Paid = %f, Minimum Required = %f",
            sale.name,
            total_order,
            total_paid,
            minimum_required
        )
        
        is_full_paid = total_paid >= total_order
        logger.info(
            "Is full paid for sale999999999999999999999 %s: %s",
            sale.name,
            is_full_paid
        )

        if not is_full_paid:
            logger.info(
                "Payment not full for sale000000000000000000000 %s: Total Paid = %f, Minimum Required = %f",
                sale.name,
                total_paid,
                minimum_required
            )
            if total_paid < minimum_required:
            # Check for approved minimum advance request
                approved_request = self.env["resonnocare.advance.approval.request"].search(
                    [
                        ("sale_order_id", "=", sale.id),
                        ("state", "=", "approved"),
                    ],
                    order="id desc",
                    limit=1,
                )
                logger.info(
                    "Found approved advance request for sale111111111111111111111 %s: %s",
                    sale.name,
                    bool(approved_request)
                )

                if not approved_request:
                    error_msg = (
                        "❌ SCM Order cannot be created: Payment/Advance requirement not met.\n\n"
                        f"📊 Sale Order: {sale.name}\n"
                        f"💰 Total Amount: {total_order:.2f}\n"
                        f"💳 Amount Paid: {total_paid:.2f}\n"
                        f"📈 Paid Percentage: {(total_paid/total_order*100 if total_order else 0):.2f}%\n"
                        f"⚠️ Minimum Required (30%): {minimum_required:.2f}\n\n"
                        "📋 Required Actions (choose ONE):\n"
                        "───────────────────────────────────────\n"
                        "1️⃣ Collect FULL PAYMENT (100% of total amount)\n"
                        "   → Click 'Collect Balance' button and create invoice\n"
                        "   → Register payment for the full amount\n\n"
                        "   OR\n\n"
                        "2️⃣ Get MINIMUM ADVANCE APPROVAL (at least 30%)\n"
                        "   → Click 'Min Advance Request' button\n"
                        "   → Create a request with minimum {:.2f}\n"
                        "   → Get it APPROVED by authorized person\n\n"
                        "After completing either option, try creating SCM Order again."
                    ).format(minimum_required)
                    raise UserError(error_msg)
                
                # Check if paid amount meets the approved minimum
                if total_paid < approved_request.requested_min_advance:
                    error_msg = (
                        "❌ SCM Order cannot be created: Paid amount below approved minimum.\n\n"
                        f"💰 Total Amount: {total_order:.2f}\n"
                        f"💳 Amount Paid: {total_paid:.2f}\n"
                        f"✅ Approved Minimum Advance: {approved_request.requested_min_advance:.2f}\n\n"
                        f"📋 Required Action:\n"
                        f"───────────────────────────────────────\n"
                        f"Please collect additional payment of {approved_request.requested_min_advance - total_paid:.2f}\n"
                        f"to reach the approved minimum advance amount.\n\n"
                        f"Click 'Collect Balance' button to create invoice and register payment."
                    )
                    raise UserError(error_msg)
            
        # CHECK 4: Configuration
        clinic = self.clinic_id
        if not clinic:
            raise UserError(
                "❌ SCM Order cannot be created: Clinic not configured.\n"
                "Please select a clinic for this appointment."
            )
        
        company = clinic.company_id or self.env.company
        if not company:
            raise UserError(
                "❌ SCM Order cannot be created: Company not configured.\n"
                "Please ensure the clinic has a company associated."
            )
        
        ho_warehouse = company.ho_warehouse_id
        if not ho_warehouse:
            error_msg = (
                "❌ SCM Order cannot be created: HO Warehouse not configured.\n\n"
                f"🏢 Company: {company.name}\n"
                f"📦 HO Warehouse: Not Set\n\n"
                "📋 Required Action:\n"
                "───────────────────────────────────────\n"
                "Go to Company settings and configure:\n"
                "1. Settings → Companies → Select your company\n"
                "2. Set 'HO Warehouse' field\n"
                "3. Save and try again"
            )
            raise UserError(error_msg)
        
        source_location = company.ho_hearing_aid_sale_location_id or ho_warehouse.lot_stock_id
        if not source_location:
            error_msg = (
                "❌ SCM Order cannot be created: Source location not configured.\n\n"
                f"🏢 Company: {company.name}\n"
                f"📦 HO Warehouse: {ho_warehouse.name}\n"
                f"📍 Source Location: Not Set\n\n"
                "📋 Required Action:\n"
                "───────────────────────────────────────\n"
                "Configure HO Hearing Aid Sale Location:\n"
                "1. Go to Company settings\n"
                "2. Set 'HO Hearing Aid Sale Location' field\n"
                "   (Or ensure HO Warehouse has a default stock location)\n"
                "3. Save and try again"
            )
            raise UserError(error_msg)
        
        destination_location = clinic.hearing_aid_sale_location_id or clinic.stock_location_id
        if not destination_location:
            error_msg = (
                "❌ SCM Order cannot be created: Destination location not configured.\n\n"
                f"🏥 Clinic: {clinic.name}\n"
                f"📍 Destination Location: Not Set\n\n"
                "📋 Required Action:\n"
                "───────────────────────────────────────\n"
                "Configure Clinic Hearing Aid Sale Location:\n"
                "1. Go to Clinic master\n"
                "2. Set 'Hearing Aid Sale Location' field\n"
                "   (Or ensure Clinic has a default stock location)\n"
                "3. Save and try again"
            )
            raise UserError(error_msg)
        
        picking_type = ho_warehouse.int_type_id if ho_warehouse else False
        if not picking_type:
            error_msg = (
                "❌ SCM Order cannot be created: Internal picking type not configured.\n\n"
                f"🏢 Company: {company.name}\n"
                f"📦 HO Warehouse: {ho_warehouse.name}\n"
                f"📋 Picking Type: Not Set\n\n"
                "📋 Required Action:\n"
                "───────────────────────────────────────\n"
                "Configure Internal Picking Type:\n"
                "1. Go to Warehouse settings\n"
                "2. Set 'Internal Transfers' picking type\n"
                "3. Save and try again"
            )
            raise UserError(error_msg)
        
        # CHECK 5: Products have stock data
        for line in self.device_sale_line_ids:
            product = line.product_id
            if not product:
                error_msg = (
                    "❌ SCM Order cannot be created: Device line missing product.\n\n"
                    f"Line: {line.id}\n"
                    "Please ensure all device lines have a product selected."
                )
                raise UserError(error_msg)
            
            if product.type not in ['product', 'consu']:
                error_msg = (
                    f"❌ SCM Order cannot be created: Product '{product.display_name}' is not storable.\n\n"
                    f"Product Type: {product.type}\n"
                    "Only storable products (Stockable or Consumable) can be used in SCM orders.\n\n"
                    "Please use a different product or change the product type in product settings."
                )
                raise UserError(error_msg)
        
        # All checks passed - create supply request
        # Requested qty calculation
        request_qty_by_product = defaultdict(float)
        available_cache = {}
        consumed_qty = defaultdict(float)
        
        for line in self.device_sale_line_ids:
            product = line.product_id
            ordered_qty = line.product_uom_qty or 0.0
            if ordered_qty <= 0:
                continue
            
            if self.pre_booking:
                req_qty = ordered_qty
            else:
                if product.id not in available_cache:
                    available_cache[product.id] = self._get_available_qty_in_location(
                        product, destination_location
                    )
                remaining = max(available_cache[product.id] - consumed_qty[product.id], 0.0)
                req_qty = max(ordered_qty - remaining, 0.0)
                consumed_qty[product.id] += ordered_qty
            
            if req_qty > 0:
                request_qty_by_product[product.id] += req_qty
        
        if not request_qty_by_product:
            raise UserError(
                "❌ SCM Order cannot be created: No products require supply.\n\n"
                "All requested products are already available in stock.\n"
                "No supply order needed for this appointment."
            )
        
        # Create the supply picking
        move_vals = []
        for product_id, qty in request_qty_by_product.items():
            product = self.env["product.product"].browse(product_id)
            move_vals.append(
                (
                    0,
                    0,
                    {
                        "name": product.display_name,
                        "product_id": product.id,
                        "product_uom_qty": qty,
                        "product_uom": product.uom_id.id,
                        "location_id": source_location.id,
                        "location_dest_id": destination_location.id,
                        "company_id": company.id,
                    },
                )
            )
        
        supply_picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": source_location.id,
                "location_dest_id": destination_location.id,
                "origin": f"{self.appointment_id or self.display_name}",
                "company_id": company.id,
                "move_ids_without_package": move_vals,
            }
        )
        supply_picking.action_confirm()
        return supply_picking

    def action_generate_device_sale(self):
        for rec in self:
            if rec.sale_order_id:
                raise UserError("Bill already generated for this appointment.")

            if not rec.appointment_id:
                raise UserError("Please confirm the appointment before billing.")

            if rec.status in ("cancelled", "no_show"):
                raise UserError("Cannot bill a cancelled or no-show appointment.")

            if not rec.patient_id:
                raise UserError("Please select a patient before billing.")

            if rec.diagnostic_item_ids:
                raise UserError(
                    "Service sale already prepared for this appointment. "
                    "You can only bill services or devices, not both."
                )

            if not rec.device_sale_line_ids:
                raise UserError("Please add devices before billing.")

            if not rec.clinic_id or not rec.clinic_id.warehouse_id:
                raise UserError("Clinic warehouse is not configured.")

            if not rec.clinic_id.hearing_aid_sale_location_id:
                raise UserError(
                    "Clinic hearing aid sale location is not configured."
                )

            order_lines = []
            serial_by_product = {}

            for line in rec.device_sale_line_ids:
                product = line.product_id
                if not product:
                    raise UserError("Device line is missing a product.")
                if product.type != "consu":
                    raise UserError(
                        f"Product '{product.display_name}' must be a storable product."
                    )

                if product.tracking == "serial":
                    if line.product_uom_qty != 1:
                        raise UserError(
                            f"Quantity must be 1 for serial-tracked device '{product.display_name}'."
                        )
                    if line.serial_lot_id:
                        serial_by_product.setdefault(product.id, []).append(line.serial_lot_id.id)
                    elif not rec.pre_booking:
                        raise UserError(
                            f"Please select serial number for device '{product.display_name}'."
                        )

                if line.is_ear_mould:
                    if not line.ear_mould_form_id:
                        raise UserError(
                            f"Please fill Ear Mould Form for '{product.display_name}' before billing."
                        )
                    if not line.ear_mould_form_id.is_minimum_complete:
                        raise UserError(
                            f"Ear Mould Form for '{product.display_name}' is incomplete. "
                            "Please fill Order Type and Mould Type."
                        )

                order_lines.append(
                    (0, 0, {
                        "product_id": product.id,
                        "product_uom_qty": line.product_uom_qty,
                        "price_unit": product.lst_price,
                        "name": product.display_name,
                    })
                )

            sale = self.env["sale.order"].create({
                "partner_id": rec.patient_id.id,
                "patient_id": rec.patient_id.id,
                "clinic_id": rec.clinic_id.id,
                "warehouse_id": rec.clinic_id.warehouse_id.id,
                "origin": rec.appointment_id,
                "order_line": order_lines,
            })
            # Force GST matrix taxes on auto-generated lines.
            sale.order_line._apply_fixed_tax_from_matrix()

            sale.action_confirm()
            self._apply_device_sale_picking_locations(
                sale, rec.clinic_id.hearing_aid_sale_location_id
            )

            # Reserve only user-selected serials for serial-tracked devices.
            for picking in sale.picking_ids.filtered(lambda p: p.picking_type_code == "outgoing"):
                for move in picking.move_ids_without_package:
                    if move.product_id.tracking != "serial":
                        continue
                    lot_ids = serial_by_product.get(move.product_id.id) or []
                    if lot_ids:
                        move.lot_ids = [(6, 0, lot_ids)]
                    elif not rec.pre_booking:
                        raise UserError(
                            f"Selected serial number is missing for '{move.product_id.display_name}'."
                        )
                
                # MUST assign picking to reserve quants in stock system
                # Without this, reserved_quantity stays 0 and same serial gets allocated to multiple customers
                if picking.state == "confirmed":
                    picking.action_assign()

            rec.sale_order_id = sale.id

            # rec._create_ho_supply_request_for_device_booking()

    def action_open_patient_reports(self):
        self.ensure_one()

        if self.sale_type != "device":
            raise UserError("Patient reports are only available for device appointments.")

        if not self.sale_order_id:
            raise UserError("Please generate device sale before creating HO Supply Request.")

        if not self.device_sale_line_ids:
            raise UserError("No device sale lines found for this appointment.")

        # Duplicate check
        existing = self.env["stock.picking"].search([
            ("origin", "=", self.appointment_id or self.display_name),
            ("picking_type_code", "=", "internal"),
            ("state", "not in", ("cancel",)),
        ], limit=1)

        if existing:
            raise UserError("SCM Order already created for this appointment.")

        result = self._create_ho_supply_request_for_device_booking()

        if not result:
            raise UserError(
                "Cannot create SCM Order. Please ensure all required steps are completed before generating the order."
            )

       
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "SCM Order Created",
                "message": f"HO Supply Request successfully created: {result.name}",
                "type": "success",  # success | warning | danger | info
                "sticky": False,    # True = manually close karna hoga
            },
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._apply_calendar_datetime_defaults(vals)
            if not vals.get("source") and vals.get("patient_id"):
                patient = self.env["res.partner"].browse(vals["patient_id"])
                mapped = self._get_source_from_patient(patient)
                if mapped:
                    vals["source"] = mapped
        return super().create(vals_list)

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        self._apply_calendar_datetime_defaults(vals)
        return vals

    def _apply_calendar_datetime_defaults(self, vals):
        """Map calendar datetime defaults to appointment date/time fields.
        Calendar quick-create usually sends default_appointment_start_datetime.
        """
        if vals.get("appointment_date") and vals.get("appointment_start_time") not in (False, None):
            return

        dt_val = vals.get("appointment_start_datetime")
        if not dt_val:
            dt_val = self.env.context.get("default_appointment_start_datetime")
        if not dt_val:
            return

        dt = fields.Datetime.to_datetime(dt_val)
        if not dt:
            return

        # Convert to current user timezone to preserve clicked slot meaning.
        dt_local = fields.Datetime.context_timestamp(self, dt).replace(tzinfo=None)
        vals.setdefault("appointment_date", dt_local.date())
        vals.setdefault("appointment_start_time", dt_local.hour + (dt_local.minute / 60.0))

    def write(self, vals):
        res = super().write(vals)
        if "patient_id" in vals:
            for rec in self:
                mapped = rec._get_source_from_patient(rec.patient_id)
                if mapped and rec.source != mapped:
                    rec.source = mapped
        return res

    def action_view_bill(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Sale Order",
            "res_model": "sale.order",
            "view_mode": "form",
            "res_id": self.sale_order_id.id,
            "target": "current",
        }

    def action_collect_balance(self):
        self.ensure_one()
        sale = self._get_effective_sale_order()
        if not sale:
            raise UserError("No sale order linked to this appointment.")

        return {
            "type": "ir.actions.act_window",
            "name": "Create invoice(s)",
            "res_model": "sale.advance.payment.inv",
            "view_mode": "form",
            "target": "new",
            "context": {
                "active_model": "sale.order",
                "active_ids": [sale.id],
                "active_id": sale.id,
            },
        }

    def action_create_fitting_appointment(self):
        self.ensure_one()
        fitting_type = self.env["resonnocare.appointment.type"].search(
            [("name", "ilike", "fitting"), ("active", "=", True)],
            limit=1,
        )
        if not fitting_type:
            raise UserError(
                "Appointment Type 'Fitting' is not configured. Please create/activate it in Masters."
            )
        
        sale = self._get_effective_sale_order()
        if sale:
            minimum_required = (sale.amount_total or 0.0) * 0.30
            total_paid = self._get_total_paid_for_sale(sale)
            if total_paid < minimum_required:
                approved_request = self.env["resonnocare.advance.approval.request"].search(
                    [
                        ("sale_order_id", "=", sale.id),
                        ("state", "=", "approved"),
                    ],
                    order="id desc",
                    limit=1,
                )
                if not approved_request or not approved_request.requested_min_advance:
                    raise UserError(
                        "Fitting appointment cannot be created because paid advance is below the required threshold.\n"
                        f"Minimum Required (30%): {minimum_required:.2f}\n"
                        f"Currently Paid: {total_paid:.2f}\n\n"
                        "To continue with a lower advance, create and get approval for a Min Advance Request from this Appointment or related Sale Order."
                    )
                if total_paid < approved_request.requested_min_advance:
                    raise UserError(
                        "Min Advance Request is approved, but paid amount is still below the approved minimum.\n"
                        f"Approved Minimum Advance: {approved_request.requested_min_advance:.2f}\n"
                        f"Paid: {total_paid:.2f}"
                    )
        
        # Get the audiologist from the original appointment if available
        audiologist_id = self.audiologist_id.id if self.audiologist_id else False
        technician_id = self.technician_id.id if self.technician_id else False
        
        # Create the fitting appointment with proper link
        fitting_appointment = self.env["resonnocare.appointment"].create({
            'parent_appointment_id': self.id,  # Link to original appointment
            'patient_id': self.patient_id.id,
            'clinic_id': self.clinic_id.id,
            'appointment_type_id': fitting_type.id,
            'sale_type': 'device',
            'sale_order_id': self.sale_order_id.id,
            'appointment_date': fields.Date.today(),
            'appointment_start_time': self.appointment_start_time,  # Copy start time
            'audiologist_id': audiologist_id,  # Copy audiologist
            'technician_id': technician_id,  # Copy technician
            'source': self.source,
            'status': 'draft',
            'notes': f"Fitting appointment created from {self.appointment_id or self.name}",
        })
        
        # Return to open the newly created fitting appointment
        return {
            "type": "ir.actions.act_window",
            "name": "Fitting Appointment",
            "res_model": "resonnocare.appointment",
            "view_mode": "form",
            "res_id": fitting_appointment.id,
            "target": "current",
            "context": {
                "default_parent_appointment_id": self.id,
                "default_patient_id": self.patient_id.id,
                "default_clinic_id": self.clinic_id.id,
                "default_appointment_type_id": fitting_type.id,
                "default_sale_type": "device",
                "default_sale_order_id": self.sale_order_id.id,
                "default_audiologist_id": audiologist_id,
                "default_technician_id": technician_id,
            },
        }

    def action_open_min_advance_request(self):
        self.ensure_one()
        if self.sale_type != "device":
            raise UserError("Min advance request is applicable only for device sales.")
        sale = self._get_effective_sale_order()
        if not sale:
            raise UserError("No sale order linked to this appointment.")
        min_advance = (sale.amount_total or 0.0) * 0.30
        total_paid = self._get_total_paid_for_sale(sale)
        suggested = total_paid if total_paid > 0 else min_advance
        if suggested >= min_advance:
            suggested = max(min_advance - 1, 0)
        return {
            "type": "ir.actions.act_window",
            "name": "Min Advance Requests",
            "res_model": "resonnocare.advance.approval.request",
            "view_mode": "list,form",
            "domain": [("sale_order_id", "=", sale.id)],
            "context": {
                "default_sale_order_id": sale.id,
                "default_appointment_id": self.id,
                "default_requested_min_advance": suggested,
            },
            "target": "current",
        }


    @api.constrains("diagnostic_item_ids")
    def _lock_diagnostics_after_billing(self):
        for rec in self:
            if (
                rec.sale_order_id
                and rec._origin
                and rec._origin.diagnostic_item_ids != rec.diagnostic_item_ids
            ):
                raise UserError(
                    "Diagnostic tests cannot be modified after billing."
                )

    @api.constrains("diagnostic_item_ids", "device_sale_line_ids")
    def _check_service_or_device_sale(self):
        for rec in self:
            if rec.diagnostic_item_ids and rec.device_sale_line_ids:
                raise UserError(
                    "You can only sell services or devices from one appointment, not both."
                )
            if rec.sale_type == "service" and rec.device_sale_line_ids:
                raise UserError(
                    "Sale Type is set to Service. Please remove device lines."
                )
            if rec.sale_type == "device" and rec.diagnostic_item_ids:
                raise UserError(
                    "Sale Type is set to Device. Please remove diagnostic tests."
                )
            if rec.pre_booking and rec.sale_type != "device":
                raise UserError("Pre-booking can only be used for device sale type.")
            if rec.pre_booking and rec.diagnostic_item_ids:
                raise UserError("Pre-booking is only for device orders; remove diagnostic tests.")
    
    def _schedule_after_payment(self):
        import logging
        _logger = logging.getLogger(__name__)
        for rec in self:
            _logger.info(f"Scheduling appointment {rec.id}, current status: {rec.status}")
            if rec.status == "draft":
                rec.status = "scheduled"
                _logger.info(f"Appointment {rec.id} scheduled, new status: {rec.status}")
            else:
                _logger.info(f"Appointment {rec.id} not scheduled, status is not draft")




    @api.depends("appointment_start_time", "appointment_type_id")
    def _compute_end_time(self):
        for rec in self:
            if rec.appointment_start_time and rec.appointment_type_id:
                duration = rec.appointment_type_id.duration or 0
                rec.appointment_end_time = rec.appointment_start_time + (
                    duration / 60.0
                )
            else:
                rec.appointment_end_time = 0.0

    @api.depends("appointment_date", "appointment_start_time", "appointment_end_time", "appointment_type_id")
    def _compute_start_end_datetime(self):
        for rec in self:
            rec.appointment_start_datetime = False
            rec.appointment_end_datetime = False

            if not rec.appointment_date or not rec.appointment_start_time:
                continue

            date_val = fields.Date.to_date(rec.appointment_date)
            start_minutes = int(round(rec.appointment_start_time * 60))
            start_hour = start_minutes // 60
            start_minute = start_minutes % 60

            start_local = datetime.combine(date_val, time(start_hour % 24, start_minute))
            tz = pytz.timezone(self.env.user.tz or "UTC")
            start_utc = tz.localize(start_local).astimezone(pytz.UTC).replace(tzinfo=None)
            rec.appointment_start_datetime = start_utc

            end_time = rec.appointment_end_time
            if not end_time and rec.appointment_type_id:
                end_time = rec.appointment_start_time + ((rec.appointment_type_id.duration or 0) / 60.0)

            if end_time:
                end_minutes = int(round(end_time * 60))
                delta_minutes = end_minutes - start_minutes
                end_local = start_local + timedelta(minutes=delta_minutes)
                end_utc = tz.localize(end_local).astimezone(pytz.UTC).replace(tzinfo=None)
                rec.appointment_end_datetime = end_utc

    @api.depends("status")
    def _compute_color_index(self):
        for rec in self:
            if rec.status == "draft":
                rec.color_index = 0  # grey
            elif rec.status in ("scheduled", "checked_in"):
                rec.color_index = 2
            elif rec.status in ("in_consultation", "completed"):
                rec.color_index = 3
            else:
                rec.color_index = 4

    def _get_end_time_float(self):
        self.ensure_one()
        if self.appointment_end_time:
            return self.appointment_end_time
        if self.appointment_type_id and self.appointment_start_time:
            return self.appointment_start_time + ((self.appointment_type_id.duration or 0) / 60.0)
        return 0.0

    def _get_busy_audiologist_ids(self):
        self.ensure_one()
        if not self.appointment_date or not self.appointment_start_time:
            return set()

        end_time = self._get_end_time_float()
        if not end_time:
            return set()

        overlaps = self.search([
            ("clinic_id", "=", self.clinic_id.id),
            ("appointment_date", "=", self.appointment_date),
            ("status", "not in", ("cancelled", "no_show")),
            ("audiologist_id", "!=", False),
            ("id", "!=", self.id),
            ("appointment_start_time", "<", end_time),
            ("appointment_end_time", ">", self.appointment_start_time),
        ])
        return set(overlaps.mapped("audiologist_id").ids)

    def _get_busy_technician_ids(self):
        self.ensure_one()
        if not self.appointment_date or not self.appointment_start_time:
            return set()

        end_time = self._get_end_time_float()
        if not end_time:
            return set()

        overlaps = self.search([
            ("clinic_id", "=", self.clinic_id.id),
            ("appointment_date", "=", self.appointment_date),
            ("status", "not in", ("cancelled", "no_show")),
            ("technician_id", "!=", False),
            ("id", "!=", self.id),
            ("appointment_start_time", "<", end_time),
            ("appointment_end_time", ">", self.appointment_start_time),
        ])
        return set(overlaps.mapped("technician_id").ids)

    @api.depends("appointment_date", "appointment_start_time", "appointment_end_time", "appointment_type_id", "clinic_id")
    def _compute_available_audiologists(self):
        for rec in self:
            if not rec.clinic_id:
                rec.available_audiologist_ids = False
                continue

            audiologists = self.env["hr.employee"].search([
                ("clinic_id", "=", rec.clinic_id.id),
                ("clinic_role", "=", "doctor"),
                ("active", "=", True),
            ])

            if not rec.appointment_date or not rec.appointment_start_time:
                rec.available_audiologist_ids = audiologists
                continue

            busy_ids = rec._get_busy_audiologist_ids()
            rec.available_audiologist_ids = audiologists.filtered(lambda d: d.id not in busy_ids)

    @api.depends("clinic_id")
    def _compute_available_technicians(self):
        for rec in self:
            if not rec.clinic_id:
                rec.available_technician_ids = False
                continue
            technicians = self.env["hr.employee"].search(
                [
                    ("clinic_id", "=", rec.clinic_id.id),
                    ("clinic_role", "=", "technician"),
                    ("active", "=", True),
                ]
            )
            if not rec.appointment_date or not rec.appointment_start_time:
                rec.available_technician_ids = technicians
                continue
            busy_ids = rec._get_busy_technician_ids()
            rec.available_technician_ids = technicians.filtered(
                lambda t: t.id not in busy_ids
            )

    @api.depends_context("uid")
    def _compute_can_edit_clinic(self):
        user = self.env.user
        can_edit = self.env.uid == SUPERUSER_ID or user.has_group("base.group_system") or user.has_group(
            "resonnocare_base.group_resonnocare_super_admin"
        ) or user.has_group(
            "resonnocare_base.group_clinic_admin"
        )
        for rec in self:
            rec.can_edit_clinic = can_edit

    @api.onchange("clinic_id")
    def _onchange_clinic_autofill_staff(self):
        for rec in self:
            if not rec.clinic_id:
                rec.audiologist_id = False
                rec.technician_id = False
                continue

            if rec.audiologist_id and rec.audiologist_id.clinic_id != rec.clinic_id:
                rec.audiologist_id = False
            if rec.technician_id and rec.technician_id.clinic_id != rec.clinic_id:
                rec.technician_id = False

    def _is_resonnocare_admin_user(self):
        self.ensure_one()
        return self.env.user.has_group("base.group_system") or self.env.user.has_group(
            "resonnocare_base.group_resonnocare_super_admin"
        )

    def _has_valid_start_time(self):
        self.ensure_one()
        return self.appointment_start_time not in (False, None) and self.appointment_start_time > 0.0

    def _is_past_appointment_slot(self):
        self.ensure_one()
        if (
            not self.appointment_date
            or self.appointment_start_time in (False, None)
        ):
            return False
        now_local = fields.Datetime.context_timestamp(self, fields.Datetime.now()).replace(
            tzinfo=None
        )

        date_val = fields.Date.to_date(self.appointment_date)
        start_minutes = int(round(self.appointment_start_time * 60))
        start_hour = start_minutes // 60
        start_minute = start_minutes % 60
        start_local = datetime.combine(date_val, time(start_hour % 24, start_minute))

        # 1-minute tolerance avoids false positives while user is editing.
        return start_local < (now_local - timedelta(minutes=1))

    @api.onchange("appointment_date", "appointment_start_time")
    def _onchange_block_past_slot_for_non_admin(self):
        if self.env.user.has_group("base.group_system") or self.env.user.has_group(
            "resonnocare_base.group_resonnocare_super_admin"
        ):
            return
        for rec in self:
            if rec.appointment_date and not rec._has_valid_start_time():
                return {
                    "warning": {
                        "title": _("Start Time Required"),
                        "message": _("Please select appointment start time."),
                    }
                }
            if rec.appointment_start_time in (False, None):
                continue
            if rec.appointment_date and rec._is_past_appointment_slot():
                rec.appointment_start_time = False
                return {
                    "warning": {
                        "title": _("Past Slot Not Allowed"),
                        "message": _(
                            "Past date/time cannot be selected for appointments."
                        ),
                    }
                }



    @api.constrains("audiologist_id", "appointment_date", "appointment_start_time", "appointment_end_time", "appointment_type_id", "status")
    def _check_doctor_conflicts(self):
        for rec in self:
            end_time = rec._get_end_time_float()
            if not end_time or not rec.appointment_date or not rec.appointment_start_time:
                continue

            if rec.audiologist_id:
                conflict = self.search([
                    ("clinic_id", "=", rec.clinic_id.id),
                    ("audiologist_id", "=", rec.audiologist_id.id),
                    ("appointment_date", "=", rec.appointment_date),
                    ("status", "not in", ("cancelled", "no_show")),
                    ("id", "!=", rec.id),
                    ("appointment_start_time", "<", end_time),
                    ("appointment_end_time", ">", rec.appointment_start_time),
                ], limit=1)

                if conflict:
                    raise UserError(
                        f"Audiologist {rec.audiologist_id.name} already has an overlapping appointment "
                        f"({conflict.appointment_id or conflict.id}). Please choose another time or audiologist."
                    )

    @api.constrains("technician_id", "appointment_date", "appointment_start_time", "appointment_end_time", "appointment_type_id", "status")
    def _check_technician_conflicts(self):
        for rec in self:
            end_time = rec._get_end_time_float()
            if not end_time or not rec.appointment_date or not rec.appointment_start_time:
                continue

            if rec.technician_id:
                conflict = self.search([
                    ("clinic_id", "=", rec.clinic_id.id),
                    ("technician_id", "=", rec.technician_id.id),
                    ("appointment_date", "=", rec.appointment_date),
                    ("status", "not in", ("cancelled", "no_show")),
                    ("id", "!=", rec.id),
                    ("appointment_start_time", "<", end_time),
                    ("appointment_end_time", ">", rec.appointment_start_time),
                ], limit=1)

                if conflict:
                    raise UserError(
                        f"Technician {rec.technician_id.name} already has an overlapping appointment "
                        f"({conflict.appointment_id or conflict.id}). Please choose another time or technician."
                    )

    @api.constrains("appointment_date", "appointment_start_time")
    def _check_past_slot_for_non_admin(self):
        for rec in self:
            if rec.appointment_date and not rec._has_valid_start_time():
                raise ValidationError(_("Appointment start time is mandatory."))
            if rec._is_resonnocare_admin_user():
                continue
            if rec.appointment_start_time in (False, None):
                continue
            if rec.appointment_type_id.name != 'Fitting' and rec.appointment_date and rec._is_past_appointment_slot():
                raise ValidationError(
                    _(
                        "Past date/time is not allowed for appointments."
                    )
                )

    # ---------------------------------------------------------------------
    # STATE TRANSITION ACTIONS (STRICT)
    # ---------------------------------------------------------------------


    def action_confirm(self):
        for rec in self:
            if rec.status != "draft":
                raise UserError("Only draft appointments can be confirmed.")
            if rec.is_diagnostic_service_type and rec.sale_type == "device":
                raise UserError(
                    _(
                        "Device sale type is not allowed for Diagnostic/Service appointment type."
                    )
                )
            if rec.is_device_goods_type and rec.sale_type == "service":
                raise UserError(
                    _(
                        "Service sale type is not allowed for Device/Goods appointment type."
                    )
                )
            if (
                rec.sale_type == "device"
                and not rec.parent_appointment_id
                and not rec._patient_has_prescribed_diagnostic()
            ):
                raise UserError(
                    _(
                        "This patient is not eligible for a device appointment yet.\n"
                        "Please complete a service/diagnostic appointment on the same day and ensure outcome includes 'Prescribed'."
                    )
                )
            if not rec._has_valid_start_time():
                raise ValidationError(_("Appointment start time is mandatory."))
            if (not rec._is_resonnocare_admin_user()) and rec._is_past_appointment_slot():
                raise ValidationError(
                    _("Past date/time is not allowed for appointments.")
                )
            if not rec.audiologist_id:
                raise UserError("Please select an audiologist before confirming the appointment.")
            # if not rec.technician_id:
            #     raise UserError("Please select a technician before confirming the appointment.")

            # ✅ STEP 2: Generate appointment ID based on clinic and patient mapping
            count = self.env["resonnocare.appointment"].search_count([
                ("clinic_id", "=", rec.clinic_id.id),
                ("patient_id", "=", rec.patient_id.id),
                ("appointment_id", "!=", False)  # Exclude records without ID to avoid counting self if not set
            ])
            clinic_num = rec.clinic_id.clinic_code.split('-')[-1] if '-' in rec.clinic_id.clinic_code else rec.clinic_id.clinic_code
            patient_num = rec.patient_id.patient_id.split()[-1] if rec.patient_id.patient_id else ''
            rec.appointment_id = f"APT-{clinic_num}/{patient_num}/{count + 1}"
            rec.status = "scheduled"
        return rec    

    def _patient_has_prescribed_diagnostic(self):
        self.ensure_one()
        if not self.patient_id or not self.appointment_date:
            return False
        domain = [
            ("patient_id", "=", self.patient_id.id),
            ("sale_type", "=", "service"),
            ("status", "=", "completed"),
            ("appointment_date", "=", self.appointment_date),
            ("id", "!=", self.id),
            "|",
            "|",
            ("appointment_outcome_ids.outcome", "ilike", "prescrib"),
            ("appointment_outcome_ids.meaning", "ilike", "prescrib"),
            ("appointment_outcome_ids.code", "ilike", "rx"),
        ]
        return bool(self.env["resonnocare.appointment"].search_count(domain))

    def action_check_in(self):
        for rec in self:
            if rec.status != "scheduled":
                raise UserError("Only scheduled appointments can be checked in.")
            rec.status = "checked_in"

    def action_start_consultation(self):
        for rec in self:
            if rec.status != "checked_in":
                raise UserError("Consultation can start only after check-in.")
            rec.status = "in_consultation"

    def action_complete(self):
        self.ensure_one()
        if self.status != "in_consultation":
            raise UserError("Only appointments in consultation can be completed.")
        if self.parent_appointment_id and (self.balance_due or 0.0) > 0:
            raise UserError(
                _(
                    "Fitting appointment cannot be completed while balance due is greater than 0."
                )
            )
        wizard = self.env["resonnocare.appointment.complete.wizard"].create(
            {"appointment_id": self.id}
        )
        return {
            "type": "ir.actions.act_window",
            "name": "Complete Appointment",
            "res_model": "resonnocare.appointment.complete.wizard",
            "view_mode": "form",
            "view_id": self.env.ref(
                "resonnocare_appointment.view_resonnocare_appointment_complete_wizard_form"
            ).id,
            "res_id": wizard.id,
            "target": "new",
        }

    def action_no_show(self):
        for rec in self:
            if rec.status != "scheduled":
                raise UserError("Only scheduled appointments can be marked as no-show.")
            rec.status = "no_show"

    def action_cancel(self):
        for rec in self:
            if rec.status not in ("draft", "scheduled"):
                raise UserError(
                    "Only draft or scheduled appointments can be cancelled."
                )
            rec.status = "cancelled"


class ResonnocareAppointmentPreBookingExt(models.Model):
    _inherit = "resonnocare.appointment"

    pre_booking = fields.Boolean(string="Pre-Booking")
    expected_delivery_date = fields.Date(string="Expected Delivery Date")
