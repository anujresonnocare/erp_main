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
from odoo import api, models, _
from odoo.exceptions import ValidationError


class Users(models.Model):
    _inherit = "res.users"

    @api.constrains('groups_id')
    def _check_one_user_type(self):
        super(Users, self)._check_one_user_type()

        h1 = self.env.ref('jt_education_base.group_school', False)
        h2 = self.env.ref('jt_education_base.group_college', False)

        if not h1 or not h2:
            # A user cannot be in a non-existant group
            return

        for user in self:
            if user._has_multiple_groups([h1.id, h2.id]):
                raise ValidationError(_("A user cannot have both School and College.\n"))
