# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta


class ResonnocareRepairContract(models.Model):
    _name = "resonnocare.repair.contract"
    _description = "Resonnocare Repair Service Contract"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Contract Number",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    patient_id = fields.Many2one(
        "res.partner",
        string="Patient",
        required=True,
        domain=[("is_patient", "=", True)],
        tracking=True,
    )
    clinic_id = fields.Many2one(
        "resonnocare.clinic",
        string="Clinic",
        required=True,
        default=lambda self: self.env.user.clinic_id or self.env.user.employee_id.clinic_id,
        tracking=True,
    )

    patient_lot_ids = fields.Many2many(
        "stock.lot",
        compute="_compute_patient_lot_ids",
        string="Patient Fitted Serials",
    )

    # Left Ear Device details
    left_lot_id = fields.Many2one(
        "stock.lot",
        string="Left Serial Number",
        domain="[('id', 'in', patient_lot_ids)]",
        tracking=True,
    )
    left_product_id = fields.Many2one(
        "product.product",
        string="Left Model",
        tracking=True,
    )
    left_manufacturer_id = fields.Many2one(
        "res.partner",
        string="Left Manufacturer",
        related="left_product_id.manufacturer_id",
        readonly=True,
    )
    left_device_code = fields.Char(
        string="Left Device Code",
        tracking=True,
    )
    left_warranty_end_date = fields.Date(
        string="Left Warranty End Date",
        compute="_compute_warranty_info",
        store=True,
    )
    left_is_under_warranty = fields.Boolean(
        string="Left Under Warranty",
        compute="_compute_warranty_info",
        store=True,
    )
    left_repair_notes = fields.Text(
        string="Left Ear Repair Notes",
        tracking=True,
    )

    # Right Ear Device details
    right_lot_id = fields.Many2one(
        "stock.lot",
        string="Right Serial Number",
        domain="[('id', 'in', patient_lot_ids)]",
        tracking=True,
    )
    right_product_id = fields.Many2one(
        "product.product",
        string="Right Model",
        tracking=True,
    )
    right_manufacturer_id = fields.Many2one(
        "res.partner",
        string="Right Manufacturer",
        related="right_product_id.manufacturer_id",
        readonly=True,
    )
    right_device_code = fields.Char(
        string="Right Device Code",
        tracking=True,
    )
    right_warranty_end_date = fields.Date(
        string="Right Warranty End Date",
        compute="_compute_warranty_info",
        store=True,
    )
    right_is_under_warranty = fields.Boolean(
        string="Right Under Warranty",
        compute="_compute_warranty_info",
        store=True,
    )
    right_repair_notes = fields.Text(
        string="Right Ear Repair Notes",
        tracking=True,
    )

    warranty_end_date = fields.Date(
        string="Warranty End Date",
        compute="_compute_warranty_info",
        store=True,
    )
    is_under_warranty = fields.Boolean(
        string="Is Under Warranty",
        compute="_compute_warranty_info",
        store=True,
    )

    date_required = fields.Date(
        string="Date Required / Commitment Date",
        tracking=True,
    )
    notes = fields.Text(
        string="General Repair Notes / Symptoms",
        tracking=True,
    )

    # Repair Checklists Left & Right
    dead_left = fields.Boolean("Dead (Left)")
    dead_right = fields.Boolean("Dead (Right)")
    intermittent_left = fields.Boolean("Intermittent (Left)")
    intermittent_right = fields.Boolean("Intermittent (Right)")
    distorted_left = fields.Boolean("Distorted (Left)")
    distorted_right = fields.Boolean("Distorted (Right)")
    recircuit_left = fields.Boolean("Recase / Recircuit (Left)")
    recircuit_right = fields.Boolean("Recase / Recircuit (Right)")
    programming_left = fields.Boolean("Programming (Left)")
    programming_right = fields.Boolean("Programming (Right)")
    battery_door_left = fields.Boolean("Battery Door (Left)")
    battery_door_right = fields.Boolean("Battery Door (Right)")
    shell_left = fields.Boolean("Shell (Left)")
    shell_right = fields.Boolean("Shell (Right)")
    retube_left = fields.Boolean("Retube (Left)")
    right_retube = fields.Boolean("Retube (Right)")
    volume_control_left = fields.Boolean("Volume Control (Left)")
    volume_control_right = fields.Boolean("Volume Control (Right)")
    wax_management_left = fields.Boolean("Wax Management (Left)")
    wax_management_right = fields.Boolean("Wax Management (Right)")
    general_service_left = fields.Boolean("General Service (Left)")
    general_service_right = fields.Boolean("General Service (Right)")
    
    quotation_required = fields.Boolean(
        string="Quotation Required",
        default=False,
    )
    is_non_repairable = fields.Boolean(
        string="Non-Repairable (BER)",
        default=False,
        tracking=True,
    )

    billing_mode = fields.Selection(
        [
            ("corporate", "Corporate"),
            ("revenue_sharing", "Revenue Sharing"),
        ],
        string="Billing Mode",
        required=True,
        default="corporate",
        tracking=True,
    )
    handling_charges = fields.Float(
        string="Handling Charges",
        default=500.0,
        tracking=True,
    )
    estimated_repair_charges = fields.Float(
        string="Estimated Repair Charges",
        default=0.0,
        tracking=True,
        help="Estimated repair cost communicated to the patient before sending to lab.",
    )
    repair_charges = fields.Float(
        string="Actual Repair Charges",
        default=0.0,
        tracking=True,
        help="Final repair charges as per vendor invoice.",
    )
    charges_communicated_date = fields.Date(
        string="Charges Communicated On",
        readonly=True,
        tracking=True,
    )
    gst_rate = fields.Float(
        string="GST Rate (%)",
        compute="_compute_gst_rate",
        store=True,
        readonly=False,
        default=18.0,
    )
    
    # State-based Tax Split Columns
    cgst_rate = fields.Float("CGST Rate (%)", compute="_compute_tax_breakup", store=True)
    cgst_amount = fields.Float("CGST Amount", compute="_compute_tax_breakup", store=True)
    sgst_rate = fields.Float("SGST Rate (%)", compute="_compute_tax_breakup", store=True)
    sgst_amount = fields.Float("SGST Amount", compute="_compute_tax_breakup", store=True)
    igst_rate = fields.Float("IGST Rate (%)", compute="_compute_tax_breakup", store=True)
    igst_amount = fields.Float("IGST Amount", compute="_compute_tax_breakup", store=True)

    tax_amount = fields.Float(
        string="Tax Amount",
        compute="_compute_charges_totals",
        store=True,
    )
    total_charges = fields.Float(
        string="Total Charges",
        compute="_compute_charges_totals",
        store=True,
    )
    total_charges_in_words = fields.Char(
        string="Total Charges (In Words)",
        compute="_compute_total_charges_in_words",
        store=True,
    )

    payment_method = fields.Selection(
        [
            ("cash", "Cash"),
            ("cheque", "Cheque"),
            ("card", "Credit/Debit Card"),
            ("upi", "UPI"),
        ],
        string="Payment Method",
        tracking=True,
    )
    cheque_number = fields.Char(string="Cheque Number")
    cheque_date = fields.Date(string="Cheque Date")
    cheque_bank_name = fields.Char(string="Cheque Bank")
    payment_status = fields.Selection(
        [
            ("pending", "Pending"),
            ("realized", "Realized / Paid"),
        ],
        string="Payment Status",
        default="pending",
        tracking=True,
    )
    hospital_receipt_number = fields.Char(
        string="Hospital Receipt Number",
        tracking=True,
    )
    hospital_receipt_file = fields.Binary(
        string="Hospital Payment Receipt",
        attachment=True,
    )
    hospital_receipt_filename = fields.Char(string="Hospital Receipt Filename")
    finance_approval_status = fields.Selection(
        [
            ("not_required", "Not Required"),
            ("pending", "Pending Finance Approval"),
            ("approved", "Finance Approved"),
        ],
        string="Finance Approval Status",
        default="not_required",
        tracking=True,
    )
    vendor_id = fields.Many2one(
        "res.partner",
        string="Repair Lab / Vendor",
        domain=[("supplier_rank", ">", 0)],
        tracking=True,
    )
    dispatch_tracking_number = fields.Char(
        string="Dispatch Tracking ID",
        tracking=True,
    )
    dispatch_date = fields.Date(string="Dispatch Date")
    dispatch_vendor_id = fields.Many2one(
        "res.partner",
        string="Dispatch / Courier Vendor",
        domain=[("supplier_rank", ">", 0)],
        tracking=True,
        help="Courier or transport vendor used for dispatch (e.g. BlueDart, DTDC, DHL). Helps SCM track and communicate with the vendor.",
    )
    dispatch_courier_name = fields.Char(
        string="Courier Reference / Label",
        tracking=True,
        help="Optional label or reference. e.g. Hand Delivery, Local Courier",
    )
    dispatch_awb_number = fields.Char(
        string="AWB / Tracking Number",
        tracking=True,
    )
    expected_return_date = fields.Date(
        string="Expected Return Date from Lab",
        tracking=True,
    )
    scm_notes = fields.Text(
        string="SCM Follow-up Notes",
        tracking=True,
    )
    vendor_invoice_number = fields.Char(
        string="Vendor Invoice Number",
        tracking=True,
    )
    vendor_invoice_date = fields.Date(string="Vendor Invoice Date")
    vendor_invoice_amount = fields.Float(string="Vendor Invoice Amount")
    vendor_invoice_file = fields.Binary(
        string="Vendor Invoice Copy",
        attachment=True,
    )
    received_date = fields.Date(string="Received Date at Clinic")
    handover_date = fields.Date(string="Handover Date to Patient")
    patient_acknowledgement = fields.Binary(
        string="Patient Acknowledgement Sign/Receipt",
        attachment=True,
    )
    patient_acknowledgement_filename = fields.Char(string="Acknowledgement Filename")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("estimate_communicated", "Estimate Communicated"),
            ("declined", "Declined (No Service)"),
            ("estimate_approved", "Estimate Approved"),
            ("paid", "Paid / Receipt Attached"),
            ("dispatched", "Dispatched to Lab"),
            ("received", "Received at Clinic"),
            ("delivered", "Handover / Done"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )
    invoice_id = fields.Many2one(
        "account.move",
        string="Customer Invoice",
        readonly=True,
    )
    stock_picking_id = fields.Many2one(
        "stock.picking",
        string="Repair GRN Transfer",
        readonly=True,
    )
    repair_appointment_id = fields.Many2one(
        "resonnocare.appointment",
        string="Repair Appointment",
        readonly=True,
        copy=False,
        tracking=True,
    )
    repair_appointment_count = fields.Integer(
        string="Appointment Count",
        compute="_compute_repair_appointment_count",
    )

    currency_id = fields.Many2one(
        "res.currency",
        related="clinic_id.company_id.currency_id",
        readonly=True,
    )

    def _compute_repair_appointment_count(self):
        for rec in self:
            rec.repair_appointment_count = 1 if rec.repair_appointment_id else 0

    def action_view_repair_appointment(self):
        self.ensure_one()
        if not self.repair_appointment_id:
            raise UserError(_("No repair appointment linked to this contract."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Repair Appointment"),
            "res_model": "resonnocare.appointment",
            "view_mode": "form",
            "res_id": self.repair_appointment_id.id,
        }

    @api.depends("patient_id")
    def _compute_patient_lot_ids(self):
        for rec in self:
            if not rec.patient_id:
                rec.patient_lot_ids = False
                continue
            lot_ids = set()
            move_lines = self.env["stock.move.line"].search([
                ("picking_id.partner_id", "=", rec.patient_id.id),
                ("picking_id.state", "=", "done"),
                ("lot_id", "!=", False),
            ])
            if move_lines:
                lot_ids.update(move_lines.mapped("lot_id").ids)

            app_lines = self.env["resonnocare.appointment.device.line"].search([
                ("appointment_id.patient_id", "=", rec.patient_id.id),
                ("serial_lot_id", "!=", False),
            ])
            if app_lines:
                lot_ids.update(app_lines.mapped("serial_lot_id").ids)

            rec.patient_lot_ids = self.env["stock.lot"].browse(list(lot_ids))

    @api.onchange("patient_id")
    def _onchange_patient_serial_domain(self):
        """Safeguard: return dynamic domain for serial number fields
        to ensure only patient-specific serials are shown."""
        if self.patient_id and self.patient_lot_ids:
            return {
                "domain": {
                    "left_lot_id": [("id", "in", self.patient_lot_ids.ids)],
                    "right_lot_id": [("id", "in", self.patient_lot_ids.ids)],
                }
            }
        return {
            "domain": {
                "left_lot_id": [("id", "=", False)],
                "right_lot_id": [("id", "=", False)],
            }
        }

    @api.onchange("patient_id")
    def _onchange_patient_id(self):
        if not self.patient_id:
            self.left_lot_id = False
            self.left_product_id = False
            self.right_lot_id = False
            self.right_product_id = False
            return

        if self.patient_id.clinic_id:
            self.clinic_id = self.patient_id.clinic_id

        # First, try to find delivered serial numbers via Stock Moves (Sales/POS)
        move_lines = self.env["stock.move.line"].search([
            ("picking_id.partner_id", "=", self.patient_id.id),
            ("picking_id.state", "=", "done"),
            ("picking_id.picking_type_code", "=", "outgoing"),
            ("lot_id", "!=", False)
        ], order="date desc", limit=2)

        lots = []
        if move_lines:
            lots = [line.lot_id for line in move_lines]
        else:
            # Fallback: check custom appointment device lines
            app_lines = self.env["resonnocare.appointment.device.line"].search([
                ("appointment_id.patient_id", "=", self.patient_id.id),
                ("serial_lot_id", "!=", False)
            ], order="id desc", limit=2)
            lots = [line.serial_lot_id for line in app_lines]

        # Ensure unique lots
        unique_lots = []
        for lot in lots:
            if lot not in unique_lots:
                unique_lots.append(lot)

        if unique_lots:
            left_prod = unique_lots[0].product_id
            self.left_lot_id = unique_lots[0]
            self.left_product_id = left_prod
            self.left_device_code = left_prod.default_code
            
            # Determine Vendor (Repair Lab) from Left Product
            if hasattr(left_prod, 'manufacturer_id') and left_prod.manufacturer_id:
                self.vendor_id = left_prod.manufacturer_id
            elif left_prod.seller_ids:
                self.vendor_id = left_prod.seller_ids[0].partner_id

            if len(unique_lots) > 1:
                right_prod = unique_lots[1].product_id
                self.right_lot_id = unique_lots[1]
                self.right_product_id = right_prod
                self.right_device_code = right_prod.default_code
                
                # Fallback: if vendor not found from left, try right
                if not self.vendor_id:
                    if hasattr(right_prod, 'manufacturer_id') and right_prod.manufacturer_id:
                        self.vendor_id = right_prod.manufacturer_id
                    elif right_prod.seller_ids:
                        self.vendor_id = right_prod.seller_ids[0].partner_id
            else:
                self.right_lot_id = False
                self.right_product_id = False
                self.right_device_code = False
        else:
            self.left_lot_id = False
            self.left_product_id = False
            self.left_device_code = False
            self.right_lot_id = False
            self.right_product_id = False
            self.right_device_code = False

    @api.onchange("left_lot_id")
    def _onchange_left_lot_id(self):
        if self.left_lot_id:
            self.left_product_id = self.left_lot_id.product_id
            if self.left_product_id:
                self.left_device_code = self.left_product_id.default_code
                if hasattr(self.left_product_id, 'manufacturer_id') and self.left_product_id.manufacturer_id:
                    self.vendor_id = self.left_product_id.manufacturer_id
                elif self.left_product_id.seller_ids:
                    self.vendor_id = self.left_product_id.seller_ids[0].partner_id

    @api.onchange("left_product_id")
    def _onchange_left_product_id(self):
        if self.left_product_id and not self.left_device_code:
            self.left_device_code = self.left_product_id.default_code
            if not self.vendor_id:
                if hasattr(self.left_product_id, 'manufacturer_id') and self.left_product_id.manufacturer_id:
                    self.vendor_id = self.left_product_id.manufacturer_id
                elif self.left_product_id.seller_ids:
                    self.vendor_id = self.left_product_id.seller_ids[0].partner_id

    @api.onchange("right_lot_id")
    def _onchange_right_lot_id(self):
        if self.right_lot_id:
            self.right_product_id = self.right_lot_id.product_id
            if self.right_product_id:
                self.right_device_code = self.right_product_id.default_code
                if not self.vendor_id:
                    if hasattr(self.right_product_id, 'manufacturer_id') and self.right_product_id.manufacturer_id:
                        self.vendor_id = self.right_product_id.manufacturer_id
                    elif self.right_product_id.seller_ids:
                        self.vendor_id = self.right_product_id.seller_ids[0].partner_id

    @api.onchange("right_product_id")
    def _onchange_right_product_id(self):
        if self.right_product_id and not self.right_device_code:
            self.right_device_code = self.right_product_id.default_code
            if not self.vendor_id:
                if hasattr(self.right_product_id, 'manufacturer_id') and self.right_product_id.manufacturer_id:
                    self.vendor_id = self.right_product_id.manufacturer_id
                elif self.right_product_id.seller_ids:
                    self.vendor_id = self.right_product_id.seller_ids[0].partner_id

    def _calculate_device_warranty(self, lot, product, patient):
        if not patient or (not lot and not product):
            return False, False

        today = fields.Date.context_today(self)

        # 1) Direct Lot Warranty End Date
        if lot and lot.warranty_end_date:
            return lot.warranty_end_date, lot.warranty_end_date >= today

        prod = product or (lot.product_id if lot else False)
        if not prod:
            return False, False

        months = getattr(prod, 'warranty_months', 0) or getattr(prod.product_tmpl_id, 'warranty_months', 0) or 0
        if months <= 0:
            months = 12

        # 2) Fitting Closure Date (Completed fitting appointment)
        fitting_app = self.env["resonnocare.appointment"].search([
            ("patient_id", "=", patient.id),
            ("status", "=", "completed"),
            ("appointment_type_id.name", "ilike", "fitting"),
        ], order="appointment_date desc, id desc", limit=1)

        if fitting_app and fitting_app.appointment_date:
            end_date = fitting_app.appointment_date + relativedelta(months=months)
            return end_date, end_date >= today

        # 3) Stock Picking Delivery Date (Outgoing delivery)
        picking_line = self.env["stock.move.line"].search([
            ("picking_id.partner_id", "=", patient.id),
            ("picking_id.state", "=", "done"),
            ("picking_id.picking_type_code", "=", "outgoing"),
            ("product_id", "=", prod.id),
        ], order="date desc, id desc", limit=1)

        if picking_line and picking_line.picking_id.date_done:
            end_date = picking_line.picking_id.date_done.date() + relativedelta(months=months)
            return end_date, end_date >= today

        # 4) Customer Invoice Date fallback
        inv_line = self.env["account.move.line"].search([
            ("partner_id", "=", patient.id),
            ("product_id", "=", prod.id),
            ("parent_state", "=", "posted"),
            ("move_id.move_type", "=", "out_invoice"),
        ], order="date desc, id desc", limit=1)

        if inv_line and inv_line.move_id.invoice_date:
            end_date = inv_line.move_id.invoice_date + relativedelta(months=months)
            return end_date, end_date >= today

        return False, False

    @api.depends(
        "left_lot_id",
        "right_lot_id",
        "left_product_id",
        "right_product_id",
        "patient_id",
        "left_lot_id.warranty_end_date",
        "right_lot_id.warranty_end_date",
    )
    def _compute_warranty_info(self):
        today = fields.Date.context_today(self)
        for rec in self:
            left_end, left_under = rec._calculate_device_warranty(rec.left_lot_id, rec.left_product_id, rec.patient_id)
            rec.left_warranty_end_date = left_end
            rec.left_is_under_warranty = left_under

            right_end, right_under = rec._calculate_device_warranty(rec.right_lot_id, rec.right_product_id, rec.patient_id)
            rec.right_warranty_end_date = right_end
            rec.right_is_under_warranty = right_under

            dates = [d for d in [left_end, right_end] if d]
            if dates:
                rec.warranty_end_date = max(dates)
                rec.is_under_warranty = rec.warranty_end_date >= today
            else:
                rec.warranty_end_date = False
                rec.is_under_warranty = False

    @api.depends("left_product_id", "right_product_id")
    def _compute_gst_rate(self):
        for rec in self:
            matrix = self.env["resonnocare.gst.rate.matrix"].search(
                [("hsn_sac_code", "=", "998729")], limit=1
            )
            if matrix:
                rec.gst_rate = matrix.gst_rate
            else:
                rec.gst_rate = 18.0

    @api.depends("clinic_id", "clinic_id.state_id", "patient_id", "patient_id.state_id", "gst_rate", "handling_charges", "repair_charges", "estimated_repair_charges")
    def _compute_tax_breakup(self):
        for rec in self:
            # Use actual repair charges if entered, otherwise fall back to estimated
            effective_repair = rec.repair_charges if rec.repair_charges > 0 else rec.estimated_repair_charges
            subtotal = rec.handling_charges + effective_repair
            clinic_state = rec.clinic_id.state_id
            patient_state = rec.patient_id.state_id

            if clinic_state and patient_state and clinic_state == patient_state:
                rec.cgst_rate = rec.gst_rate / 2.0
                rec.sgst_rate = rec.gst_rate / 2.0
                rec.igst_rate = 0.0
            else:
                rec.cgst_rate = 0.0
                rec.sgst_rate = 0.0
                rec.igst_rate = rec.gst_rate

            rec.cgst_amount = subtotal * (rec.cgst_rate / 100.0)
            rec.sgst_amount = subtotal * (rec.sgst_rate / 100.0)
            rec.igst_amount = subtotal * (rec.igst_rate / 100.0)

    @api.depends("handling_charges", "repair_charges", "estimated_repair_charges", "cgst_amount", "sgst_amount", "igst_amount")
    def _compute_charges_totals(self):
        for rec in self:
            # Use actual repair charges if entered, otherwise fall back to estimated
            effective_repair = rec.repair_charges if rec.repair_charges > 0 else rec.estimated_repair_charges
            subtotal = rec.handling_charges + effective_repair
            rec.tax_amount = rec.cgst_amount + rec.sgst_amount + rec.igst_amount
            rec.total_charges = subtotal + rec.tax_amount

    @api.depends("total_charges", "currency_id")
    def _compute_total_charges_in_words(self):
        for rec in self:
            currency = rec.currency_id or self.env.company.currency_id
            if currency and rec.total_charges > 0.0:
                rec.total_charges_in_words = currency.amount_to_text(rec.total_charges)
            else:
                rec.total_charges_in_words = ""

    def action_communicate_charges(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Charges can only be communicated from Draft state."))
            if rec.handling_charges <= 0 and rec.estimated_repair_charges <= 0:
                raise ValidationError(_("Please enter Handling Charges or Estimated Repair Charges before communicating to the patient."))
            rec.write({
                "state": "estimate_communicated",
                "charges_communicated_date": fields.Date.context_today(self),
            })

    def action_patient_decline(self):
        for rec in self:
            if rec.state not in ("draft", "estimate_communicated"):
                raise UserError(_("Patient can only decline from Draft or Estimate Communicated state."))
            rec.write({"state": "declined"})

    def action_confirm(self):
        for rec in self:
            if rec.state not in ("draft", "estimate_communicated"):
                raise UserError(_("Contract can only be confirmed from Draft or Estimate Communicated state."))
            if not rec.patient_id:
                raise ValidationError(_("Patient must be selected before confirmation."))
            if not rec.left_lot_id and not rec.right_lot_id and not rec.left_product_id and not rec.right_product_id:
                raise ValidationError(_("At least one Serial Number or Product Model (Left or Right) must be selected before confirmation."))
            
            # Generate Sequence
            if rec.name == _("New"):
                seq = self.env["ir.sequence"].next_by_code("resonnocare.repair.contract") or _("New")
                rec.name = seq

            # Auto-create Repair Appointment
            if not rec.repair_appointment_id:
                rec._create_repair_appointment()
                
            rec.write({"state": "estimate_approved"})

    def _create_repair_appointment(self):
        """Auto-create a Repair/Service appointment linked to this contract."""
        self.ensure_one()
        AppointmentType = self.env["resonnocare.appointment.type"]
        Appointment = self.env["resonnocare.appointment"]

        # Find or create 'Repair' appointment type
        repair_type = AppointmentType.search(
            [("name", "ilike", "repair")], limit=1
        )
        if not repair_type:
            repair_type = AppointmentType.search(
                [("name", "ilike", "service")], limit=1
            )
        if not repair_type:
            repair_type = AppointmentType.create({
                "name": "Repair",
                "duration": 30,
                "sale_type": "service",
            })

        # Default appointment date to today
        today = fields.Date.context_today(self)

        # Determine audiologist — current user's employee if they are an audiologist
        audiologist = False
        if self.env.user.employee_id and self.env.user.employee_id.clinic_role == 'doctor':
            audiologist = self.env.user.employee_id.id

        appointment_vals = {
            "patient_id": self.patient_id.id,
            "clinic_id": self.clinic_id.id,
            "appointment_type_id": repair_type.id,
            "appointment_date": today,
            "appointment_start_time": 10.0,  # Default 10:00 AM
            "source": "walkin",
            "notes": _("Auto-created from Repair Contract: %s") % self.name,
        }
        if audiologist:
            appointment_vals["audiologist_id"] = audiologist

        appointment = Appointment.create(appointment_vals)
        self.repair_appointment_id = appointment.id

    def action_pay(self):
        for rec in self:
            if rec.state != "estimate_approved":
                raise UserError(_("Payment can only be recorded for an Estimate Approved contract."))

            if rec.billing_mode == "corporate":
                if not rec.payment_method:
                    raise ValidationError(_("Please select a Payment Method."))
                if rec.payment_method == "cheque":
                    if not rec.cheque_number or not rec.cheque_date or not rec.cheque_bank_name:
                        raise ValidationError(_("Cheque details (number, date, bank) are mandatory for Cheque payments."))
                    rec.write({
                        "finance_approval_status": "pending",
                        "payment_status": "pending",
                    })
                else:
                    rec.write({
                        "finance_approval_status": "not_required",
                        "payment_status": "realized",
                        "state": "paid",
                    })
            else:  # revenue_sharing
                if not rec.hospital_receipt_number or not rec.hospital_receipt_file:
                    raise ValidationError(_("Hospital Receipt Number and Receipt File are mandatory in Revenue Sharing mode."))
                rec.write({
                    "payment_status": "realized",
                    "state": "paid",
                    "finance_approval_status": "not_required",
                })

    def action_finance_approve(self):
        self.ensure_one()
        if self.finance_approval_status != "pending":
            raise UserError(_("This contract is not waiting for Finance approval."))
        self.write({
            "finance_approval_status": "approved",
            "payment_status": "realized",
            "state": "paid",
        })

    def action_dispatch(self):
        for rec in self:
            if rec.state != "paid":
                raise UserError(_("Hearing Aid can only be dispatched after payment is recorded/cleared."))
            if not rec.vendor_id or not rec.dispatch_tracking_number:
                raise ValidationError(_("Vendor (Lab) and Dispatch Tracking ID are mandatory for dispatching."))
            rec.write({
                "state": "dispatched",
                "dispatch_date": fields.Date.context_today(self),
            })

    def action_receive_at_clinic(self):
        for rec in self:
            if rec.state != "dispatched":
                raise UserError(_("Cannot receive at clinic unless dispatched to Vendor."))
            if not rec.vendor_invoice_number or not rec.vendor_invoice_amount:
                raise ValidationError(_("SCM/Purchase team must update Vendor Invoice details (Number and Amount) before receiving."))

            picking_type = self.env["stock.picking.type"].search([
                ("code", "=", "incoming"),
                ("warehouse_id", "=", rec.clinic_id.warehouse_id.id)
            ], limit=1)
            
            dest_location = rec.clinic_id.repair_service_location_id or picking_type.default_location_dest_id
            src_location = rec.vendor_id.property_stock_supplier or self.env.ref("stock.stock_location_suppliers", raise_if_not_found=False)
            if not src_location:
                src_location = self.env["stock.location"].search([("usage", "=", "supplier")], limit=1)

            prod = rec.left_product_id or rec.right_product_id
            lot = rec.left_lot_id or rec.right_lot_id

            if picking_type and dest_location and src_location and prod:
                picking_vals = {
                    "picking_type_id": picking_type.id,
                    "location_id": src_location.id,
                    "location_dest_id": dest_location.id,
                    "origin": rec.name,
                    "partner_id": rec.vendor_id.id,
                }
                picking = self.env["stock.picking"].create(picking_vals)
                
                move_vals = {
                    "name": _("Repair Return: %s") % prod.name,
                    "product_id": prod.id,
                    "product_uom_qty": 1.0,
                    "product_uom": prod.uom_id.id,
                    "picking_id": picking.id,
                    "location_id": src_location.id,
                    "location_dest_id": dest_location.id,
                }
                move = self.env["stock.move"].create(move_vals)
                
                picking.action_confirm()
                picking.action_assign()
                
                if lot:
                    for move_line in move.move_line_ids:
                        move_line.write({
                            "lot_id": lot.id,
                            "quantity": 1.0,
                        })
                
                picking.button_validate()
                rec.stock_picking_id = picking.id

            rec.write({
                "state": "received",
                "received_date": fields.Date.context_today(self),
            })

    def _get_or_create_repair_product(self, code, name):
        product = self.env["product.product"].search([("default_code", "=", code)], limit=1)
        if not product:
            product = self.env["product.product"].create({
                "name": name,
                "default_code": code,
                "type": "service",
                "item_category": "repair_services",
                "list_price": 0.0,
            })
        return product

    def action_deliver(self):
        for rec in self:
            if rec.state != "received":
                raise UserError(_("Cannot handover to patient until received back at clinic."))
            if not rec.patient_acknowledgement:
                raise ValidationError(_("Patient acknowledgement signature/receipt is mandatory for delivery."))

            journal = self.env["account.journal"].search([("type", "=", "sale")], limit=1)
            
            partner = rec.patient_id
            if rec.billing_mode == "corporate":
                sharing_pct = 0.0
            else:  # revenue_sharing
                prod = rec.left_product_id or rec.right_product_id
                sharing_res = rec.clinic_id._resolve_clinic_sharing(
                    product=prod,
                    mrp=rec.total_charges
                )
                sharing_pct = sharing_res.get("sharing_percent", 0.0) or 0.0

            invoice_lines = []
            
            handling_product = rec._get_or_create_repair_product("REP_HANDLING", "Hearing Aid Repair Handling Charges")
            handling_amount = rec.handling_charges
            if sharing_pct > 0.0:
                handling_amount = handling_amount * (100.0 - sharing_pct) / 100.0
            
            if handling_amount > 0.0:
                invoice_lines.append((0, 0, {
                    "product_id": handling_product.id,
                    "name": handling_product.name,
                    "quantity": 1.0,
                    "price_unit": handling_amount,
                }))

            if not rec.is_non_repairable:
                repair_product = rec._get_or_create_repair_product("REP_SERVICE", "Hearing Aid Repair Service Charges")
                repair_amount = rec.repair_charges
                if sharing_pct > 0.0:
                    repair_amount = repair_amount * (100.0 - sharing_pct) / 100.0

                if repair_amount > 0.0:
                    invoice_lines.append((0, 0, {
                        "product_id": repair_product.id,
                        "name": repair_product.name,
                        "quantity": 1.0,
                        "price_unit": repair_amount,
                    }))

            if invoice_lines:
                invoice_vals = {
                    "move_type": "out_invoice",
                    "partner_id": partner.id,
                    "journal_id": journal.id,
                    "invoice_origin": rec.name,
                    "clinic_id": rec.clinic_id.id,
                    "invoice_line_ids": invoice_lines,
                }
                invoice = self.env["account.move"].create(invoice_vals)
                invoice.action_post()
                rec.invoice_id = invoice.id

            if rec.is_non_repairable:
                # Write-off / Scrap the devices
                scrap_loc = self.env.ref("stock.stock_location_scrapped", raise_if_not_found=False)
                if not scrap_loc:
                    scrap_loc = self.env["stock.location"].search([("scrap_location", "=", True)], limit=1)

                dest_location = rec.clinic_id.repair_service_location_id
                if not dest_location:
                    picking_type = self.env["stock.picking.type"].search([
                        ("code", "=", "incoming"),
                        ("warehouse_id", "=", rec.clinic_id.warehouse_id.id)
                    ], limit=1)
                    dest_location = picking_type.default_location_dest_id
                
                if scrap_loc and dest_location:
                    for lot, prod in [(rec.left_lot_id, rec.left_product_id), (rec.right_lot_id, rec.right_product_id)]:
                        if lot and prod:
                            scrap = self.env["stock.scrap"].create({
                                "product_id": prod.id,
                                "lot_id": lot.id,
                                "product_uom_id": prod.uom_id.id,
                                "scrap_qty": 1.0,
                                "location_id": dest_location.id,
                                "scrap_location_id": scrap_loc.id,
                                "origin": f"{rec.name} (BER)",
                                "company_id": rec.clinic_id.company_id.id
                            })
                            scrap.do_scrap()

                rec.write({
                    "state": "cancel",
                    "handover_date": fields.Date.context_today(self),
                })
            else:
                rec.write({
                    "state": "delivered",
                    "handover_date": fields.Date.context_today(self),
                })

    def action_cancel(self):
        for rec in self:
            if rec.state in ("delivered", "cancel"):
                raise UserError(_("Cannot cancel a completed or already cancelled contract."))
            rec.write({"state": "cancel"})
