# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    no_of_days = fields.Integer('Number of Days',config_parameter='fees.no_of_days')
    student_for_reward = fields.Integer('Number Of Students', config_parameter='fees.student_for_reward')
