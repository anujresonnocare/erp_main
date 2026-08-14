# -*- coding: utf-8 -*-
import base64
from datetime import datetime
from io import BytesIO

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    stn_number = fields.Char(
        string="GRN Number",
        copy=False,
        readonly=True,
        index=True,
    )
    stn_acknowledged_by_id = fields.Many2one(
        "res.users",
        string="GRN Acknowledged By",
        readonly=True,
        copy=False,
    )
    stn_acknowledged_on = fields.Datetime(
        string="GRN Acknowledged On",
        readonly=True,
        copy=False,
    )
    stn_can_acknowledge = fields.Boolean(
        compute="_compute_stn_can_acknowledge",
    )
    supply_clinic_id = fields.Many2one(
        "resonnocare.clinic",
        string="Clinic",
        compute="_compute_supply_clinic_id",
        store=True,
        index=True,
    )
    is_clinic_supply = fields.Boolean(
        string="Clinic Supply",
        compute="_compute_supply_clinic_id",
        store=True,
        index=True,
    )
    supply_warehouse_id = fields.Many2one(
        related="picking_type_id.warehouse_id",
        string="Warehouse",
        store=True,
        readonly=True,
    )
    is_supply_eligible = fields.Boolean(
        string="Supply Eligible",
        compute="_compute_is_supply_eligible",
        store=False,
        help="True if full payment done OR minimum advance request is approved.",
    )
    courier_name = fields.Char(string="Courier Name", copy=False)
    docket_number = fields.Char(string="Docket Number", copy=False, index=True)
    docket_date = fields.Date(string="Docket Date", copy=False)
    dispatch_remarks = fields.Text(string="Dispatch Remarks", copy=False)
    docket_file = fields.Binary(string="Docket File", attachment=True, copy=False)
    docket_file_name = fields.Char(string="Docket Filename", copy=False)

    @api.depends("picking_type_code", "location_dest_id")
    def _compute_supply_clinic_id(self):
        clinic_model = self.env["resonnocare.clinic"].sudo()
        for picking in self:
            picking.supply_clinic_id = False
            picking.is_clinic_supply = False
            if (
                picking.picking_type_code != "internal"
                or not picking.location_dest_id
            ):
                continue
            clinic = clinic_model.search(
                [("stock_location_id", "parent_of", picking.location_dest_id.id)],
                limit=1,
            )
            if clinic:
                picking.supply_clinic_id = clinic
                picking.is_clinic_supply = True


    def _is_clinic_destination_location(self):
        self.ensure_one()
        if not self.location_dest_id:
            return False
        return bool(
            self.env["resonnocare.clinic"].sudo().search_count(
                [("stock_location_id", "parent_of", self.location_dest_id.id)],
                limit=1,
            )
        )

    def _is_user_clinic_destination(self):
        self.ensure_one()
        user = self.env.user.sudo()
        clinic = user.clinic_id or user.employee_id.clinic_id
        if not clinic or not clinic.stock_location_id or not self.location_dest_id:
            return False
        return bool(
            self.env["stock.location"].search_count(
                [
                    ("id", "=", self.location_dest_id.id),
                    ("id", "child_of", clinic.stock_location_id.id),
                ]
            )
        )

    def _is_user_clinic_source_location(self):
        """Check if the outgoing picking is FROM the user's clinic warehouse"""
        self.ensure_one()
        user = self.env.user.sudo()
        clinic = user.clinic_id or user.employee_id.clinic_id
        if not clinic or not clinic.stock_location_id or not self.location_id:
            return False
        return bool(
            self.env["stock.location"].search_count(
                [
                    ("id", "=", self.location_id.id),
                    ("id", "child_of", clinic.stock_location_id.id),
                ]
            )
        )

    @api.depends("picking_type_code", "is_clinic_supply", "origin")
    def _compute_is_supply_eligible(self):
        # Guard: during early module upgrade, dependent models may not be loaded yet
        try:
            appointment_model = self.env["resonnocare.appointment"]
            approval_model = self.env["resonnocare.advance.approval.request"]
        except KeyError:
            for picking in self:
                picking.is_supply_eligible = True
            return

        for picking in self:
            if not picking.is_clinic_supply or not picking.origin:
                picking.is_supply_eligible = True
                continue

            appointment = appointment_model.search(
                ["|", ("appointment_id", "=", picking.origin), ("name", "=", picking.origin)],
                limit=1,
            )

            if not appointment or not appointment.sale_order_id:
                picking.is_supply_eligible = True
                continue

            sale = appointment._get_effective_sale_order()
            if not sale:
                picking.is_supply_eligible = True
                continue

            total_order = sale.amount_total or 0.0
            total_paid = appointment._get_total_paid_for_sale(sale)

            # Eligible if FULL payment done
            if total_paid >= total_order:
                picking.is_supply_eligible = True
                continue

            # Eligible if Min Advance Request EXISTS and APPROVED
            approved = approval_model.search_count(
                [("sale_order_id", "=", sale.id), ("state", "=", "approved")]
            )
            picking.is_supply_eligible = bool(approved)

    @api.depends("picking_type_code", "state", "location_dest_id", "stn_acknowledged_by_id")
    def _compute_stn_can_acknowledge(self):
        for picking in self:
            picking.stn_can_acknowledge = (
                picking.picking_type_code == "internal"
                and picking.state == "done"
                and not picking.stn_acknowledged_by_id
                and picking._is_user_clinic_destination()
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            picking_type = False
            if vals.get("picking_type_id"):
                picking_type = self.env["stock.picking.type"].browse(vals["picking_type_id"])
            code = (
                vals.get("picking_type_code")
                or (picking_type.code if picking_type else False)
            )
            if code == "internal" and not vals.get("stn_number"):
                vals["stn_number"] = self.env["ir.sequence"].next_by_code("resonnocare.grn") or self.env["ir.sequence"].next_by_code("resonnocare.stn")
        return super().create(vals_list)

    def button_validate(self):
        for picking in self:
            
            # ============================================
            # VALIDATION 1: Internal transfers (GRN input)
            # ============================================
            if picking.picking_type_code == "internal":
                if not picking._is_clinic_destination_location():
                    continue

                serial_moves = picking.move_ids_without_package.filtered(
                    lambda mv: mv.product_id.tracking == "serial" and mv.product_uom_qty > 0
                )
                for move in serial_moves:
                    lines = picking.move_line_ids.filtered(
                        lambda ml: ml.move_id == move and ml.quantity > 0
                    )
                    if not lines:
                        raise UserError(
                            _(
                                "Please open Detailed Operations and select serial numbers for '%s' before validating."
                            )
                            % move.product_id.display_name
                        )

                    missing_serial = lines.filtered(lambda ml: not ml.lot_id)
                    if missing_serial:
                        raise UserError(
                            _(
                                "Please select serial numbers before validating this clinic transfer.\n"
                                "Missing serial for: %s"
                            )
                            % move.product_id.display_name
                        )

                    invalid_qty = lines.filtered(lambda ml: ml.quantity != 1)
                    if invalid_qty:
                        raise UserError(
                            _(
                                "Serial-tracked items in clinic transfer must have quantity 1 per serial line.\n"
                                "Check: %s"
                            )
                            % move.product_id.display_name
                        )

                    total_qty = sum(lines.mapped("quantity"))
                    if total_qty != move.product_uom_qty:
                        raise UserError(
                            _(
                                "Serial lines quantity mismatch for '%s'.\n"
                                "Expected: %s, Entered in serial lines: %s"
                            )
                            % (move.product_id.display_name, move.product_uom_qty, total_qty)
                        )

            elif picking.picking_type_code == "outgoing":
                # Check if clinic has acknowledged the GRN for received stock of this specific order
                if picking._is_user_clinic_source_location():
                    clinic = self.env.user.clinic_id or self.env.user.employee_id.clinic_id
                    if clinic and clinic.stock_location_id:
                        origins = []
                        if hasattr(picking, "sale_id") and picking.sale_id:
                            if picking.sale_id.origin:
                                origins.append(picking.sale_id.origin)
                            if picking.sale_id.name:
                                origins.append(picking.sale_id.name)
                        if picking.origin:
                            origins.append(picking.origin)

                        if origins:
                            # Check if there are pending/unacknowledged internal transfers for this specific order/appointment
                            pending_grns = self.search([
                                ("picking_type_code", "=", "internal"),
                                ("state", "=", "done"),
                                ("location_dest_id", "child_of", clinic.stock_location_id.id),
                                ("origin", "in", origins),
                                ("stn_acknowledged_by_id", "=", False),  # Not acknowledged
                            ])
                            
                            if pending_grns:
                                # List the pending GRN numbers
                                pending_grn_numbers = ", ".join([grn.stn_number or grn.name for grn in pending_grns])
                                raise UserError(
                                    _(
                                        "Cannot deliver products to patient: Pending GRN (%s) must be acknowledged first.\n\n"
                                        "Please go to 'Goods in Transit' and acknowledge all pending GRNs before proceeding with deliveries."
                                    ) % pending_grn_numbers
                                )

        res = super().button_validate()

        for picking in self:
            if picking.picking_type_code != "internal" or picking.state != "done":
                continue
            if not picking._is_user_clinic_destination():
                continue
            if not picking.stn_acknowledged_by_id:
                picking.write(
                    {
                        "stn_acknowledged_by_id": self.env.user.id,
                        "stn_acknowledged_on": fields.Datetime.now(),
                    }
                )

        for picking in self:
            if picking.picking_type_code != "outgoing":
                continue

            move_lines = picking.move_line_ids.filtered(
                lambda ml: ml.lot_id and ml.quantity
            )
            for line in move_lines:
                lot = line.lot_id
                if lot.warranty_start_date:
                    continue

                months = line.product_id.product_tmpl_id.warranty_months
                if not months:
                    continue

                start_date = fields.Date.context_today(picking)
                end_date = start_date + relativedelta(months=months)

                lot.write(
                    {
                        "warranty_start_date": start_date,
                        "warranty_end_date": end_date,
                    }
                )

        return res

    def action_acknowledge_stn(self):
        for picking in self:
            if not picking.stn_can_acknowledge:
                raise UserError(_("You can only acknowledge done GRNs for your clinic."))
            picking.sudo().write(
                {
                    "stn_acknowledged_by_id": self.env.user.id,
                    "stn_acknowledged_on": fields.Datetime.now(),
                }
            )
        return True

    def action_mark_dispatched(self):
        for picking in self:
            if picking.picking_type_code != "internal" or not picking.is_clinic_supply:
                raise UserError(_("Dispatch is available only for clinic supply transfers."))
            if picking.state in ("done", "cancel"):
                raise UserError(_("Only open transfers can be marked as dispatched."))
            if not picking.courier_name or not picking.docket_number:
                raise UserError(_("Please provide Courier Name and Docket Number before dispatch."))
        return self.button_validate()

    def action_goods_returned_to_ho(self):
        """ Validate return picking from Clinic to GIT """
        for picking in self:
            if picking.state in ("done", "cancel"):
                raise UserError(_("Only open transfers can be dispatched."))
            # For clinics, they must provide courier details before returning
            if not picking.note or "Courier Details:" not in picking.note:
                # Assuming courier details are saved in note during wizard or manually
                pass
        return self.button_validate()

    def action_grn_receive_at_ho(self):
        """ Validate receipt picking from GIT to Return Warehouse """
        for picking in self:
            if picking.state in ("done", "cancel"):
                raise UserError(_("Only open transfers can be received."))
        return self.button_validate()

    def action_open_clinic_incoming_receipts(self):
        user = self.env.user.sudo()
        clinic = user.clinic_id or user.employee_id.clinic_id
        if not clinic or not clinic.warehouse_id or not clinic.stock_location_id:
            raise UserError(
                "Clinic warehouse/stock location is not configured for this user."
            )

        domain = [
            ("state", "!=", "cancel"),
            ("picking_type_code", "=", "internal"),
            ("location_dest_id", "child_of", clinic.stock_location_id.id),
        ]

        return {
            "type": "ir.actions.act_window",
            "name": "GRN Acknowledgement",
            "res_model": "stock.picking",
            "view_mode": "list,form",
            "domain": domain,
            "context": {"create": False},
        }

    def action_open_clinic_deliveries(self):
        user = self.env.user.sudo()
        clinic = user.clinic_id or user.employee_id.clinic_id
        if not clinic or not clinic.warehouse_id or not clinic.stock_location_id:
            raise UserError(
                "Clinic warehouse/stock location is not configured for this user."
            )

        domain = [
            ("state", "!=", "cancel"),
            ("picking_type_code", "=", "outgoing"),
            ("location_id", "child_of", clinic.stock_location_id.id),
        ]

        return {
            "type": "ir.actions.act_window",
            "name": "Customer Deliveries",
            "res_model": "stock.picking",
            "view_mode": "list,form",
            "domain": domain,
            "context": {"create": False},
        }

    def action_open_clinic_goods_in_transit(self):
        user = self.env.user.sudo()
        clinic = user.clinic_id or user.employee_id.clinic_id
        if not clinic or not clinic.warehouse_id or not clinic.stock_location_id:
            raise UserError(
                "Clinic warehouse/stock location is not configured for this user."
            )

        domain = [
            ("state", "=", "done"),
            ("picking_type_code", "=", "internal"),
            ("location_dest_id", "child_of", clinic.stock_location_id.id),
            ("stn_acknowledged_by_id", "=", False),
        ]

        return {
            "type": "ir.actions.act_window",
            "name": "Goods in Transit",
            "res_model": "stock.picking",
            "view_mode": "list,form",
            "domain": domain,
            "context": {"create": False},
        }


    def action_open_clinic_grn_acknowledgement(self):
        return self.action_open_clinic_incoming_receipts()

    @api.model
    def _get_order_for_supply_domain(self):
        return [
            ("picking_type_code", "=", "internal"),
            ("is_clinic_supply", "=", True),
            ("state", "not in", ("done", "cancel")),
        ]

    @api.model
    def _get_order_for_supply_records_from_context(self):
        active_ids = self.env.context.get("active_ids") or []
        records = self.browse(active_ids).exists()
        if records:
            return records
        
        # Get all supply orders
        all_pickings = self.search(self._get_order_for_supply_domain(), order="create_date desc")
        
        # ✅ FILTER: Show if (Min Advance Request EXISTS + APPROVED) OR FULL PAYMENT
        valid_pickings = self.env["stock.picking"]
        appointment_model = self.env["resonnocare.appointment"]
        
        for picking in all_pickings:
            if not picking.origin:
                valid_pickings |= picking
                continue
            
            # Try to find related appointment
            appointment = appointment_model.search(
                ["|", ("appointment_id", "=", picking.origin), ("name", "=", picking.origin)],
                limit=1,
            )
            
            if not appointment or not appointment.sale_order_id:
                valid_pickings |= picking
                continue
            
            # Check payment status
            sale = appointment._get_effective_sale_order()
            if not sale:
                valid_pickings |= picking
                continue
            
            total_order = (sale.amount_total or 0.0)
            total_paid = appointment._get_total_paid_for_sale(sale)
            
            # ✅ Show if FULL payment (100%)
            if total_paid >= total_order:
                valid_pickings |= picking
                continue
            
            # ✅ Show if Min Advance Request EXISTS + is APPROVED
            approved_request = self.env["resonnocare.advance.approval.request"].search(
                [
                    ("sale_order_id", "=", sale.id),
                    ("state", "=", "approved"),
                ],
                limit=1,
            )
            
            if approved_request:
                valid_pickings |= picking
        
        return valid_pickings

    @api.model
    def action_download_order_for_supply_excel(self):
        try:
            import openpyxl
        except Exception:
            raise UserError(_("Excel export requires python package 'openpyxl' on the server."))

        pickings = self._get_order_for_supply_records_from_context()
        if not pickings:
            raise UserError(_("No records found in Order for Supply."))

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Order for Supply"
        headers = [
            "Order For Supply No",
            "GRN Number",
            "Warehouse",
            "Clinic",
            "Product",
            "Required Qty",
            "UoM",
            "Courier Name",
            "Docket Number",
            "Docket Date (YYYY-MM-DD)",
            "Dispatch Remarks",
        ]
        ws.append(headers)

        for picking in pickings:
            for move in picking.move_ids_without_package.filtered(lambda m: m.product_id and m.product_uom_qty > 0):
                ws.append(
                    [
                        picking.name or "",
                        picking.stn_number or "",
                        picking.supply_warehouse_id.display_name or "",
                        picking.supply_clinic_id.display_name or "",
                        move.product_id.display_name or "",
                        move.product_uom_qty or 0.0,
                        move.product_uom.name or "",
                        picking.courier_name or "",
                        picking.docket_number or "",
                        picking.docket_date.isoformat() if picking.docket_date else "",
                        picking.dispatch_remarks or "",
                    ]
                )

        for cell in ws[1]:
            cell.font = openpyxl.styles.Font(bold=True)

        stream = BytesIO()
        wb.save(stream)
        file_data = base64.b64encode(stream.getvalue())
        filename = "order_for_supply_%s.xlsx" % fields.Date.today().strftime("%Y%m%d")
        attachment = self.env["ir.attachment"].sudo().create(
            {
                "name": filename,
                "datas": file_data,
                "res_model": "stock.picking",
                "res_id": pickings[:1].id or False,
                "type": "binary",
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "self",
        }

    @api.model
    def action_open_docket_upload_wizard(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Bulk Docket Upload",
            "res_model": "resonnocare.supply.docket.upload.wizard",
            "view_mode": "form",
            "target": "new",
        }
