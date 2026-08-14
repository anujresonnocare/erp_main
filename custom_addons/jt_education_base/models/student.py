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
from odoo import models, fields, api,exceptions, _
from datetime import datetime,date,timedelta
from odoo.exceptions import ValidationError

# student information


class ResPartner(models.Model):

	_inherit = ["res.partner"]
	_description = 'Student Information'
	_rec_name = 'stud_id'


	def unlink(self):
		for record in self:
			if record.is_student and record.standard and record.div:
				standard_record = self.env['student.standard'].sudo().browse(record.standard.id)
				division_record = self.env['standard.division'].sudo().browse(record.div.id)

				if standard_record and division_record:
					if standard_record.occupied_seats > 0:
						standard_record.sudo().write({
							'occupied_seats': standard_record.occupied_seats - 1,
							'vacant_seates': standard_record.capacity - (standard_record.occupied_seats - 1)
						})
		
		return super().unlink()

	def name_get(self):
		res = []
		for rec in self:
			if rec.stud_id and rec.name:
				res.append((rec.id, '%s - %s' % (rec.stud_id, rec.name)))
			else:
				res.append((rec.id, '%s' % (rec.name)))
		return res

	# def get_year(self):
	#     return str(datetime.now().year)

	# Basic student detail
	is_student = fields.Boolean('Student')
	standard = fields.Many2one('student.standard', 'Standard' ,help="Add Standard of student")
	div = fields.Many2one('standard.division', help="Add Division of student")
	curr_year = fields.Many2one('year.year', 'Current Year', help="Add current year of student")
													# ,default=get_year 
	stud_id = fields.Char('Student ID' ,copy=False, help="Student ID")
	gender = fields.Selection([('male', 'Male'), ('female', 'Female')] ,default='male')
	working_days = fields.Char('Number of Working Days', size=3, help="Total Number of Working Days")
	working_days_present = fields.Char('Number of Working Days Present', size=3, help="Total Number of days present")
	lc_apply_date = fields.Date('Application Date of Leaving Certificate', help="Application Date of Leaving Certificate")
	lc_issue_date = fields.Date('Issue Date of Leaving Certificate', help="Issue Date of Leaving Certificate")
	detension = fields.Char('No. of Time Student is Detained', help="Number of Time Student is Detained")
	promotion = fields.Selection(string='Qualified for Promoting to Next Class',
		selection=[('yes', 'Yes'), ('no','No')])

	# Personal information
	roll_no = fields.Integer('Roll Number', copy=False , help="Roll Number")
	gr_no = fields.Char("GR Number",help="General Registration Number of student")
	father_name = fields.Char('Father Name')
	surname = fields.Char('Surname')
	nickname = fields.Char('Nickname')
	mother_name = fields.Char('Mother Name')
	nationality = fields.Char('Nationality')
	mother_tonque = fields.Char('Mother Tongue')
	religion = fields.Char('Religion')
	caste = fields.Char('Caste')
	subcaste = fields.Char('SubCaste')
	birthPlace = fields.Char('Place of Birth ')
	village = fields.Many2one('village.village',"village")
	province = fields.Many2one('province.province',"Province")
	district_id = fields.Many2one('district.district','District')
	state1 = fields.Many2one('res.country.state', 'State ',related="district_id.state")
	country1 = fields.Many2one('res.country', 'Country ',related="district_id.country")
	student_history_ids = fields.One2many('student.history', 'student_id', string="Student History")

	
	birthdate = fields.Date('Date of Birth ')
	lastschool = fields.Char('Last School Attended', help="Name of last school attended")
	last_std = fields.Char('Last Standard')
	date_admission = fields.Date('Date of admission in this school', help="Enter Date of admission in this school")
	adm_standard = fields.Many2one('student.standard', 'Admission Standard', help="Enter Standard in which student got admission in this school")
	
	progress = fields.Char('Progress')
	conduct = fields.Char('Conduct')
	howknow_id = fields.Many2one('how.know', 'How Student Know Our School')
	emergency_contact = fields.Char('Emergency Contact')
	leave_date = fields.Date('Date of Leaving School', help="Date of Leaving this school")
	std_studying = fields.Char('Studying in Standard', help="Studying in Current Standard")
	studying_since = fields.Char('Studying Since',help="Studying Since in this school")
	reason_for_leave = fields.Text('Reason for Leaving school')
	remarks = fields.Text('Remarks')
	# company_type = fields.Selection(
	#     string='Company Type',
	#     selection=[('student', 'Student'), ('person',
	#                                         'Individual'), ('company', 'Company')],
	#     compute='_compute_company_type', inverse='_write_company_type')
	signature = fields.Binary("Signature")
	parentsid = fields.Many2one('res.partner',string="Parents",domain=[('is_parent', '=', True)])
	age = fields.Integer("Age",store=True)
	detailed_age = fields.Char("Detailed Age",store=True)
	company_type = fields.Selection(selection_add=[('student', 'Student')],ondelete={'student': 'cascade'})
	state = fields.Selection([('draft','Draft'),('confirm','Confirm'),('cancel','Cancel')],default="draft")
	marksheet_attachment_pdf=fields.Binary(string="Upload Marksheet")
	marksheet_attachment_pdf_file=fields.Char(string="Upload Marksheet ")
	adhar_attachment_pdf=fields.Binary(string="Upload Adhar Card")
	adhar_attachment_pdf_file=fields.Char(string="Upload Adhar Card ")
	confirm_date = fields.Date(string="Confirmation Date")
	applied_from_website = fields.Boolean('Applied from Website',default=False)	
	admission_date = fields.Datetime('Admission Date',domain=[('is_student', '=', True)])
	student_rank = fields.Integer('Student Rank')
	student_result = fields.Float('Result Percentage')
	meeting_ids = fields.One2many(comodel_name='student.meeting', inverse_name='student_id',string="Meetings")

	def update_student_ranks(self):
		self.env['student.result'].calculate_student_ranks()

	def update_student_percentage(self):
		# Find all student results linked to this student (res.partner)
		student_result_records = self.env['student.result'].search([
			('student_id', '=', self.id),
			('is_result_annual', '=', True)
		])
		# Call calculate_student_percentage on each record found
		student_result_records.calculate_student_percentage()	


	@api.model
	def _get_grace_period(self):
		return int(self.env['ir.config_parameter'].sudo().get_param('fees.no_of_days', default=3))

	# def open_wizard_academic_year(self):
	# 	self.ensure_one()
	# 	action = self.env.ref('jt_education_base.action_change_acedamic_year').read()[0]
	# 	return action

	def check_fees_and_cancel_admission(self):
		grace_period_days = self._get_grace_period()
		current_date = fields.Datetime.now()

		confirmed_students = self.env['res.partner'].search([
			('is_student', '=', True),
			('state', '=', 'confirm'),
			('admission_date', '<=', current_date - timedelta(days=grace_period_days))
		])

		for student in confirmed_students:
			fees_paid = self.env['fees.fees'].search_count([
				('student', '=', student.id),
				('payment_state', '=', 'paid')
			])

			if fees_paid == 0:
				student.cancel_state()
	def confirm_student(self):
		for rec in self:
			rec.state = 'confirm'
			rec.standard._compute_occupied_seats()
			rec.standard._compute_available_seats()
			
			if rec.applied_from_website:
				fees = rec.standard.fee
				invite_template = rec.env.ref('jt_education_base.admission_successfull_template1')
				users_to_invite = rec.env.user
				for user in users_to_invite:
					email_values = {
						'email_from': rec.env.user.email_formatted,
						'email_to': rec.email,
						'subject': 'Admission confirmation',
						'body_html': invite_template.body_html.replace('{{fees}}', str(fees))
					}
					invite_template.send_mail(user.id, force_send=True, email_values=email_values)

	def pending_fees(self):

		# Optimize by searching for relevant partners using a domain
		partners = self.env['res.partner'].search([
			('applied_from_website', '=', True),
			('admission_date', '!=', False),  # Ensure admission date exists
		])

		for partner in partners:

			# Check if curr_year name can be compared to admission_date's year
			if partner.admission_date and partner.curr_year:
				curr_year_str = partner.curr_year.name.strip()  # Remove any extra whitespace
				
				try:
					# Extract the starting and ending years from curr_year.name, assuming the format is '2023-2024'
					year_range = curr_year_str.split('-')
					start_year = int(year_range[0])  # Get the first part of the range (e.g. '2023')
					end_year = int(year_range[1])    # Get the second part of the range (e.g. '2024')
					
					# Convert admission year to integer for comparison
					admission_year = partner.admission_date.year
					
					# Check if the admission year is within the current academic year's range
					if start_year == admission_year:

						# Check if the application close date has passed
						if partner.standard.app_close_date and partner.standard.app_close_date < date.today():

							# Check if there is no fee record for this student
							fee_record = self.env['fees.fees'].search([('student', '=', partner.id)], limit=1)
							if not fee_record:
								template = self.env.ref('jt_education_base.admission_pending_fees_template')
								email_values = {
									'email_from': self.env.user.email_formatted,
									'email_to': partner.email,
									'subject': 'Fee Payment Reminder',
								}
								template.send_mail(partner.id, force_send=True, email_values=email_values)
							else:
								print("Fee record found. No email sent.")
					else:
						print("Admission year is not within the current year range. No email sent.")
				except Exception as e:
					print("Error in comparing years:", str(e))


	def cancel_state(self):
		self.state = 'cancel'
		if self.standard:
			self.standard.occupied_seats -= 1
			self.standard.vacant_seates += 1
			invite_template = self.env.ref('jt_education_base.admission_cancel_template')
			users_to_invite = self.env.user
			for user in users_to_invite:
				email_values = {
					'email_from': self.env.user.email_formatted,
					'email_to': self.email,
					'subject':'Admission Status Information'
				}
				invite_template.send_mail(user.id, force_send=True, email_values=email_values)

	
		
	@api.onchange('company_type')
	def student_chng_type(self):
		self.company_type = self.company_type

	def get_days_in_month(self,month, year):
		if month == 2:  
			if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0): 
				return 29 
			else:
				return 28
		elif month in [4, 6, 9, 11]:   
			return 30
		else:
			return 31

	@api.onchange('birthdate')
	def onchange_birthdate(self):
		if self.birthdate:
			today = date.today()
			self.age = today.year - self.birthdate.year - ((today.month, today.day) < (self.birthdate.month, self.birthdate.day))
			years = today.year - self.birthdate.year
			months = today.month - self.birthdate.month
			days = today.day - self.birthdate.day

			# Adjust for negative differences
			if days < 0:
				months -= 1
				days += self.get_days_in_month(self.birthdate.month, self.birthdate.year)
			if months < 0:
				years -= 1
				months += 12

			self.detailed_age = str(years)+"  Years  "+str(months)+"  Months  "+str(days)+"  Days  "


	@api.constrains('birthdate')
	def validation_constraints(self):
		today=fields.Date.today()
		for rec in self:

			if rec.birthdate and rec.birthdate >=today:
				raise exceptions.ValidationError(_('Invalid date of birth ..please enter correct date'))

	@api.model_create_multi
	def create(self, vals):
		res = super(ResPartner, self).create(vals)
		for stu_rec in res:
			if stu_rec.company_type == 'student':
				stu_rec.stud_id = self.env['ir.sequence'].next_by_code(
					'studentinformation.seq')	

		return res

	def get_roll_no(self):
		for record in self:
			if not record.roll_no:
				last_roll = self.search([
					('standard', '=', record.standard.id),
					('div', '=', record.div.id),
					('roll_no', '!=', False)
				], order='roll_no desc', limit=1)

				if last_roll:
					roll_no = int(last_roll.roll_no) + 1
				else:
					roll_no = 1

				record.write({'roll_no': roll_no})
			else:
				raise ValidationError("Roll number already generated for this record.")


		
	@api.onchange('is_student')
	def onchange_company_type1(self):
		super(ResPartner, self).onchange_company_type()
		if self.is_student == True:
			self.company_type = 'student'

	def _compute_company_type(self):
		for partner in self:
			if partner.is_student:
				partner.company_type = 'student'
			elif partner.is_company:
				partner.company_type = 'company'
			else:
				partner.company_type = 'person'

	@api.model
	def default_get(self, fields):
		res = super(ResPartner, self).default_get(fields)
		if self._context.get('is_student') == True:
			res.update({'is_student': True})
		return res


class StudentStandard(models.Model):
	_name = 'student.standard'
	_description = 'Student Standard'
	name = fields.Char('Standard')
	capacity = fields.Integer("Capacity")
	occupied_seats = fields.Integer("Ocuppied Seats")
	vacant_seates = fields.Integer("Seats Available")
	student_ids = fields.One2many('res.partner', 'standard', string="Students", domain=[('is_student', '=', True)])
	app_close_date = fields.Date("Application Close Date")
	

	@api.depends('student_ids')
	def _compute_occupied_seats(self):
		for standard in self:
			standard.occupied_seats = self.env['res.partner'].search_count([('standard', '=', standard.id), ('is_student', '=', True),('state','=','confirm')])

	@api.depends('occupied_seats', 'capacity')
	def _compute_available_seats(self):
		for standard in self:
			standard.vacant_seates = standard.capacity - standard.occupied_seats



class HowKnow(models.Model):
	_name = 'how.know'
	_description = 'How Know'
	_inherit = [
				'mail.thread',
				'mail.activity.mixin',
			
			   ]

	name = fields.Char('Name')

# student division


class StandardDivision(models.Model):
	_name = 'standard.division'
	_description = 'Standard Division'
	_inherit = [
				'mail.thread',
				'mail.activity.mixin',
			
			   ]
	
	name = fields.Char('Division')
	capacity = fields.Integer("Capacity")
	occupied_seats = fields.Integer("Ocuppied Seats",compute='_compute_occupied_seats', store=True)
	vacant_seates = fields.Integer("Seats Available",compute='_compute_available_seats', store=True)
	standard_id = fields.Many2one('student.standard', string='Standard')
	
	def _compute_occupied_seats(self):
		for division in self:
			division.occupied_seats = self.env['res.partner'].search_count([
				('div', '=', division.id),
				('standard', '=', division.standard_id.id), 
				('is_student', '=', True)
			])


	@api.depends('occupied_seats', 'capacity')
	def _compute_available_seats(self):
		for division in self:
			division.vacant_seates = division.capacity - division.occupied_seats

# academic year


class Year(models.Model):
	_name = 'year.year'
	_description = 'Year'

	name = fields.Char('Year')


class ResUsers(models.Model):
	_inherit = 'res.users'

	is_student = fields.Boolean(string='Is Student', compute='_compute_is_student_and_is_parent')
	is_parent = fields.Boolean(string='Is Parent', compute='_compute_is_student_and_is_parent')

	@api.depends('partner_id')
	def _compute_is_student_and_is_parent(self):
		for user in self:
			if user.partner_id:
				user.is_student = user.partner_id.is_student
				user.is_parent = user.partner_id.is_parent
			else:
				user.is_student = False
				user.is_parent = False

class StudentHistory(models.Model):
	_name = 'student.history'

	student_id = fields.Many2one("res.partner", string="Student")
	year_changed_from = fields.Many2one('year.year', string="Changed Academic Year From", help="Previous academic year")
	year_changed_to = fields.Many2one('year.year', string="Changed Academic Year To", help="New academic year")
	reason = fields.Char("Reason") 
