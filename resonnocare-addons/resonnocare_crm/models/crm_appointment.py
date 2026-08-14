# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResonnocareAppointment(models.Model):
    _inherit = "resonnocare.appointment"

    crm_lead_id = fields.Many2one(
        "crm.lead",
        string="CRM Lead",
        readonly=True,
        copy=False,
        ondelete="set null",
    )

    def _prepare_crm_lead_sync_vals(self, appointment):
        return {
            "x_appointment_id": appointment.id,
            "x_appointment_booking_datetime": fields.Datetime.now(),
        }

    def _sync_crm_lead_from_appointments(self, appointments):
        for appointment in appointments.filtered(lambda rec: rec.crm_lead_id):
            appointment.crm_lead_id.sudo().write(
                self._prepare_crm_lead_sync_vals(appointment)
            )

    @api.model_create_multi
    def create(self, vals_list):
        appointments = super().create(vals_list)
        self._sync_crm_lead_from_appointments(appointments)
        return appointments

    def write(self, vals):
        result = super().write(vals)
        self._sync_crm_lead_from_appointments(self)
        return result
