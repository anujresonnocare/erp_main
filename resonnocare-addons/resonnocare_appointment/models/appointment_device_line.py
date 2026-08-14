# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class ResonnocareAppointmentDeviceLine(models.Model):
    _name = "resonnocare.appointment.device.line"
    _description = "Appointment Device Sale Line"

    appointment_id = fields.Many2one(
        "resonnocare.appointment",
        string="Appointment",
        required=True,
        ondelete="cascade",
    )

    product_id = fields.Many2one(
        "product.product",
        string="Device",
        required=True,
        domain=[("type", "=", "consu")],
    )

    product_uom_qty = fields.Float(string="Quantity", default=1.0)

    available_lot_ids = fields.Many2many(
        "stock.lot",
        compute="_compute_available_lot_ids",
        string="Available Serials",
    )

    serial_lot_id = fields.Many2one(
        "stock.lot",
        string="Serial Number",
        domain="[('id', 'in', available_lot_ids)]",
    )

    is_ear_mould = fields.Boolean(
        string="Ear Mould Product",
        related="product_id.product_tmpl_id.is_ear_mould",
        store=True,
        readonly=True,
    )

    ear_mould_form_id = fields.Many2one(
        "resonnocare.ear.mould.form",
        string="Ear Mould Form",
        readonly=True,
        copy=False,
    )

    @api.depends("product_id", "appointment_id", "appointment_id.clinic_id")
    def _compute_available_lot_ids(self):
        quant_model = self.env["stock.quant"]
        for line in self:
            line.available_lot_ids = False
            if not line.product_id or not line.appointment_id:
                continue

            clinic = line.appointment_id.clinic_id
            source_location = (
                clinic.hearing_aid_sale_location_id
                or clinic.stock_location_id
            )
            if not source_location:
                continue

            quants = quant_model.search([
                ("product_id", "=", line.product_id.id),
                ("location_id", "child_of", source_location.id),
                ("lot_id", "!=", False),
            ])
            lot_ids = quants.filtered(
                lambda q: (q.quantity - q.reserved_quantity) > 0
            ).mapped("lot_id").ids
            line.available_lot_ids = [(6, 0, list(dict.fromkeys(lot_ids)))]

    @api.onchange("product_id", "appointment_id")
    def _onchange_product_or_appointment(self):
        for line in self:
            if line.product_id and line.product_id.tracking == "serial":
                line.product_uom_qty = 1.0
            if line.serial_lot_id and line.serial_lot_id not in line.available_lot_ids:
                line.serial_lot_id = False

    @api.constrains("product_id", "product_uom_qty", "serial_lot_id", "appointment_id")
    def _check_serial_and_qty(self):
        for line in self:
            if not line.product_id:
                continue

            if line.serial_lot_id and line.serial_lot_id.product_id != line.product_id:
                raise UserError("Selected serial number does not belong to the selected device.")

            if line.product_id.tracking == "serial":
                if line.product_uom_qty != 1:
                    raise UserError(
                        f"Quantity must be 1 for serial-tracked device '{line.product_id.display_name}'."
                    )
                if not line.serial_lot_id and not (line.appointment_id and line.appointment_id.pre_booking):
                    raise UserError(
                        f"Please select serial number for device '{line.product_id.display_name}'."
                    )

            if line.serial_lot_id and line.appointment_id:
                clinic = line.appointment_id.clinic_id
                source_location = clinic.hearing_aid_sale_location_id or clinic.stock_location_id
                if not source_location:
                    raise UserError("Clinic stock/sale location is not configured.")
                quants = self.env["stock.quant"].search([
                    ("product_id", "=", line.product_id.id),
                    ("lot_id", "=", line.serial_lot_id.id),
                    ("location_id", "child_of", source_location.id),
                ])
                available = sum((q.quantity - q.reserved_quantity) for q in quants)
                if available <= 0:
                    raise UserError(
                        f"Selected serial '{line.serial_lot_id.name}' is not available in clinic stock."
                    )

    def action_open_ear_mould_form(self):
        self.ensure_one()
        if not self.is_ear_mould:
            raise UserError("Ear Mould form is applicable only for Ear Mould products.")

        form = self.ear_mould_form_id
        if not form:
            form = self.env["resonnocare.ear.mould.form"].search(
                [("device_line_id", "=", self.id)],
                limit=1,
            )
        if form and not self.ear_mould_form_id:
            self.ear_mould_form_id = form.id

        action = {
            "type": "ir.actions.act_window",
            "name": "Ear Mould Form",
            "res_model": "resonnocare.ear.mould.form",
            "view_mode": "form",
            "target": "new",
            "context": {
                "form_view_initial_mode": "edit",
                "default_appointment_id": self.appointment_id.id,
                "default_device_line_id": self.id,
            },
        }
        if form:
            action["res_id"] = form.id
        return action
