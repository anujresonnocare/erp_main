# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ResonnocareDeviceMaintenance(models.Model):
    _name = "resonnocare.device.maintenance"
    _description = "Clinic Device Maintenance Log"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Maintenance No.",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    device_id = fields.Many2one(
        "resonnocare.device",
        string="Device / Equipment",
        required=True,
        tracking=True,
    )
    clinic_id = fields.Many2one(
        "resonnocare.clinic",
        string="Clinic / Location",
        related="device_id.clinic_id",
        store=True,
        readonly=True,
    )
    request_date = fields.Date(
        string="Request Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    resolved_date = fields.Date(
        string="Resolved Date",
        readonly=True,
        tracking=True,
    )
    description = fields.Text(
        string="Issue Description",
        required=True,
        tracking=True,
    )
    action_taken = fields.Text(
        string="Action / Rectification Taken",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("under_maintenance", "Under Maintenance"),
            ("resolved", "Resolved"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )

    def action_confirm(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft maintenance logs can be confirmed."))
            if rec.device_id.status == "maintenance":
                raise ValidationError(_("Device is already under maintenance."))
            
            # Set sequence
            if rec.name == _("New"):
                rec.name = self.env["ir.sequence"].next_by_code("resonnocare.device.maintenance") or _("New")
                
            # Lock device status
            rec.device_id.write({"status": "maintenance"})
            rec.write({"state": "under_maintenance"})

    def action_resolve(self):
        for rec in self:
            if rec.state != "under_maintenance":
                raise UserError(_("Only logs under maintenance can be resolved."))
            
            # Unlock device status
            rec.device_id.write({"status": "available"})
            rec.write({
                "state": "resolved",
                "resolved_date": fields.Date.context_today(self),
            })

    def action_cancel(self):
        for rec in self:
            if rec.state in ("resolved", "cancel"):
                raise UserError(_("Cannot cancel resolved or already cancelled log."))
            
            # Unlock device if it was locked
            if rec.state == "under_maintenance":
                rec.device_id.write({"status": "available"})
                
            rec.write({"state": "cancel"})
