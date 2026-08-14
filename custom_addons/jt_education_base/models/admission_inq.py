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
from odoo.exceptions import ValidationError


class AdmissionInquiry(models.Model):

	_name = 'admission.inquiry'
	_description = 'Student Admission Inquiry Details'
	
	_inherit = ['mail.thread', 'mail.activity.mixin']
	

	name = fields.Char(string="Name")
	inquiry_id = fields.Char('Inquiry ID' ,copy=False, help="Inquiry ID")
	fname = fields.Char(string="Father Name")
	mname = fields.Char(string="Mother Name")
	surname = fields.Char(string="Surname")
	mobile = fields.Char(string="Mobile")
	email = fields.Char(string="Email")
	phone = fields.Char(string="Phone")
	city = fields.Char(string="City")
	gr_no = fields.Char(string="Gr No.",tracking=True)
	zip_code = fields.Char(string="Zip")
	add1 = fields.Text(string="Address 1")
	add2 = fields.Text(string="Address 2")
	question = fields.Text(string='Question')
	standard_id = fields.Many2one('student.standard', 'Standard')
	howknow_id = fields.Many2one('how.know', 'How Student Know Our School')
	state_id = fields.Many2one('res.country.state', 'State')
	country_id = fields.Many2one('res.country', 'Country')
	div_id = fields.Many2one('standard.division', 'Division')
	year_id = fields.Many2one('year.year', 'Year')
	note = fields.Text("Note")
	birthdate = fields.Date("Birthdate")
	doc_attachment_pdf=fields.Binary(string="Upload File")
	doc_attachment_pdf_file=fields.Char(string="Upload File ")
	sel_gen = fields.Selection(
		[("male", "Male"), ("female", "Female")], default="male", string="Gender"
	)
	state = fields.Selection(
		[("draft", "Draft"), ("confirm", "Confirmed"), ("cancel", "Cancelled")], default="draft", string="State ",tracking=True
	)


	@api.model_create_multi
	def create(self, vals):
		res = super(AdmissionInquiry, self).create(vals)
		for rec in res:
			rec.inquiry_id = self.env['ir.sequence'].next_by_code(
				'admissioninformation.seq')
	
		return res

	def confirm_reservation_inq(self):
		for inq in self:
			if not inq.gr_no:
				raise ValidationError(_('Enter GR No. First'))
			vals={
			'is_student':True,
			'gender':inq.sel_gen,
			'name':inq.name,
			'father_name':inq.fname,
			'mother_name':inq.mname,
			'surname':inq.surname,
			'phone':inq.phone,
			'mobile':inq.mobile,
			'email':inq.email,
			'street':inq.add1,
			'street2':inq.add2,
			'city':inq.city,
			'state_id':inq.state_id.id,
			'howknow_id':inq.howknow_id.id,
			'zip':inq.zip_code,
			'country_id':inq.country_id.id,
			'gr_no':inq.gr_no,
			'curr_year':inq.year_id.id,
			'standard':inq.standard_id.id,
			'standard':inq.standard_id.id,
			'div':inq.div_id.id,
			'birthdate':inq.birthdate,
			'comment':inq.note,
			}
			stud_id = self.env['res.partner'].create(vals)

		self.state = 'confirm'

	def cancel_reservation_inq(self):
		self.state = 'cancel'
