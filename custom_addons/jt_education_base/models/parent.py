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

from odoo import fields,models,api,_

class Parent(models.Model):

	_inherit = 'res.partner'
	_description = 'Parent Information'

	def name_get(self):
		res = []
		for rec in self:
			if rec.parents_id and rec.name:
				res.append((rec.id, '%s - %s' % (rec.parents_id, rec.name)))
			else:
				res.append((rec.id, '%s' % (rec.name)))
		return res

	is_parent = fields.Boolean(string='Is Parent')
	parents_id = fields.Char('Parent ID' ,copy=False, help="Parent ID")
	# title = fields.Selection([
	#   ('miss', 'Miss'),
	#   ('mrs', 'Mrs'),
	#   ('mr', 'Mr'),
	#   ], default='mr', string="Title")
	student_ids = fields.One2many('res.partner','parentsid',string="Students",domain=[('is_student', '=', True)])
	company_type = fields.Selection(selection_add=[('parent', 'Parent')],ondelete={'parent': 'cascade'})
	work_phone = fields.Char("Work Phone")
	educaition_level = fields.Char("Educaition Level")
	occupation = fields.Char("Occupation")
	work_address = fields.Char("Work Address ")

	@api.model_create_multi
	def create(self, vals):
		res = super(Parent, self).create(vals)
		for par_rec in res:
			if par_rec.company_type == 'parent':
				par_rec.parents_id = self.env['ir.sequence'].next_by_code(
					'parent.seq')
		return res

	def _compute_company_type(self):
		for partner in self:
			if partner.is_student:
				partner.company_type = 'student'
			elif partner.is_faculty:
				partner.company_type = 'faculty'
			elif partner.is_parent:
				partner.company_type = 'parent'
			elif partner.is_company:
				partner.company_type = 'company'
			

	def _write_company_type(self):
		for partner in self:
			partner.is_company = partner.company_type == 'company'
			partner.is_student = partner.company_type == 'student'
			partner.is_faculty = partner.company_type == 'faculty'
			partner.is_parent = partner.company_type == 'parent'


	@api.onchange('company_type')
	def onchange_company_type(self):
		self.is_parent = (self.company_type == 'parent')
		self.is_student = (self.company_type == 'student')
		self.is_faculty = (self.company_type == 'faculty')
		self.is_company = (self.company_type == 'company')


	@api.model
	def default_get(self, fields):
		res = super(Parent, self).default_get(fields)
		if self._context.get('is_parent') == True:
			res.update({'is_parent': True})
		return res
