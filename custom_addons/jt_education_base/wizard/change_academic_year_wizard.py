from odoo import models, fields, api, _
from datetime import datetime, timedelta

class ChangeAcademicYearWizard(models.TransientModel):

	_name = "change.year.wizard"
	_description = "Change Year Wizard"
	

	reason_to_change = fields.Selection([('wrong_selection', 'Wrong Selection'), ('standard_upgrade', 'Standard Upgrade')])
	current_year = fields.Many2one('year.year', 'Current Year ', help="Add current year of student")
	year_to_change = fields.Many2one('year.year', 'Changed Year', help="Add current year of student")

	@api.model
	def default_get(self, fields):
		res = super(ChangeAcademicYearWizard, self).default_get(fields)
		
		active_id = self.env.context.get('active_id')
		if active_id:
			partner = self.env['res.partner'].browse(active_id)
			if partner:
				res['current_year'] = partner.curr_year.id 
				

		return res

	def year_to_change_button(self):
		active_id = self.env.context.get('active_id')
		if active_id and self.year_to_change:
			partner = self.env['res.partner'].browse(active_id)

			if partner.curr_year.id == self.year_to_change.id:
				raise models.ValidationError("The current year and the year to change are the same. No changes were made.")
			
			partner.curr_year = self.year_to_change

			self.env['student.history'].create({
				'student_id': partner.id,
				'year_changed_from': self.current_year.id,  
				'year_changed_to': self.year_to_change.id,  
				'reason': self.reason_to_change,              
			})

