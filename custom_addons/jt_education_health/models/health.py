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

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class JtHealth(models.Model):
    _name = 'health.health'
    _rec_name = 'student_id'
    _description = "Health Detail for Students and Faculties"

    type = fields.Selection(
        [('student', 'Student'), ('faculty', 'Faculty')],
        'Type', default='student', required=True)
    student_id = fields.Many2one('res.partner', string='Student', domain=[('is_student', '=', True)])
    faculty_id = fields.Many2one('res.partner', string='Faculty', domain=[('is_faculty', '=', True)])
    height = fields.Float('Height(C.M.)')
    weight = fields.Float('Weight')
    blood_group = fields.Selection(
        [('A+', 'A+ve'), ('B+', 'B+ve'), ('O+', 'O+ve'), ('AB+', 'AB+ve'),
         ('A-', 'A-ve'), ('B-', 'B-ve'), ('O-', 'O-ve'), ('AB-', 'AB-ve')],
        'Blood Group')
    physical_challenges = fields.Boolean('Physical Challenge?', default=False)
    physical_challenges_note = fields.Text('Physical Challenge')
    major_diseases = fields.Boolean('Major Diseases?', default=False)
    major_diseases_note = fields.Text('Major Diseases')
    eyeglasses = fields.Boolean('Eye Glasses?')
    eyeglasses_no = fields.Char('Eye Glasses Number', size=64)
    regular_checkup = fields.Boolean(
        'Any Regular Checkup Required?', default=False)
    health_line = fields.One2many(
        'health.health.line', 'health_id', 'Checkup Lines')

    


    @api.constrains('height', 'weight')
    def check_height_weight(self):
        if self.height <= 0.0 or self.weight <= 0.0:
            raise ValidationError(_("Enter proper height and weight!"))

     
