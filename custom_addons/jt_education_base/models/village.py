# -*- coding: utf-8 -*-
##############################################################################
#
#    Jupical Technologies Pvt. Ltd.
#    Copyright (C) 2018-TODAY Jupical Technologies Pvt. Ltd.(<https://www.jupical.io>).
#    Author: Jupical Technologies Pvt. Ltd.(<https://www.jupical.io>)
#    you can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    It is forbidden to publish, distribute, sublicense, or sell copies
#    of the Software or modified copies of the Software.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    GENERAL PUBLIC LICENSE (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import fields,models

class StudentVillage(models.Model):
    _name = 'village.village'
    _description = 'Student Village'
    _inherit = [
                'mail.thread',
                'mail.activity.mixin',
            
               ]
    

    name = fields.Char(string='Name')
    # province_id = fields.Many2one('province.province',string="Province")
    # dis_id = fields.Many2one('district.district',string="District",related="province_id.district_id")
    # state = fields.Many2one('res.country.state',string="State" ,related="dis_id.state")
    # country = fields.Many2one('res.country',string="Country",related="dis_id.country")
