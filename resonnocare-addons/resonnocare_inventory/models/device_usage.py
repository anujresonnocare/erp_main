# -*- coding: utf-8 -*-
from odoo import models, fields

class ResonnocareDeviceUsage(models.Model):
    _name = 'resonnocare.device.usage'
    _description = 'Device Usage Log'
    _order = 'id desc'

    appointment_id = fields.Many2one(
        'resonnocare.appointment',
        string='Appointment',
        required=True,
        ondelete='cascade'
    )

    device_id = fields.Many2one(
        'resonnocare.device',
        string='Device',
        required=True
    )

    clinic_id = fields.Many2one(
        'res.company',
        string='Clinic',
        required=True
    )

    status = fields.Selection(
        [
            ('planned', 'Planned'),
            ('used', 'Used'),
            ('skipped', 'Skipped'),
        ],
        default='planned',
        required=True
    )

    used_on = fields.Datetime(string='Used On')
