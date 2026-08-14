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

class Faculty(models.Model):

    _inherit = 'res.partner'
    _description = 'Faculty Information'

    def name_get(self):
        res = []
        for rec in self:
            if rec.faculty_id and rec.name:
                res.append((rec.id, '%s - %s' % (rec.faculty_id, rec.name)))
            else:
                res.append((rec.id, '%s' % (rec.name)))
        return res

    is_faculty = fields.Boolean(string='Is Faculty')
    faculty_id = fields.Char('Faculty ID' ,copy=False, help="Faculty ID")
    job_id = fields.Many2one('hr.job',string="Job Positions", help="Select appropriate Job Position")
    degree = fields.Many2one('hr.recruitment.degree', string="Degree", help="Select your Highest degree")
    specialization = fields.Char('Subject/Specialization', help="Enter Subject in which you have specialization")
    college = fields.Char('College', help="Enter Passed out college")
    board = fields.Char('Board/University', help="Enter Board/University passed out from")
    qualifying_date = fields.Date('Qualifying Date',help="Enter Qualifying Date")
    name_of_institute = fields.Char('Name of Institute/University/School')
    designation = fields.Char('Post Held/Designation', help="Enter Post/Designation held previously.")
    date_from = fields.Datetime(
        string='Date From',
        tracking=True)
    date_to = fields.Datetime(
        string='Date To',
        tracking=True)
    basic_last_salary = fields.Char('Basic Salary Last Drawn,Pay scale and Grade scale')
    duties = fields.Char('Nature Of Duties', help="Enter what kind of duties where held by you.")
    degree_attachment_filename = fields.Char(string="Upload Degree...") # field type converted in many2one to Char
    degree_attachment = fields.Binary(string="Degree Certificate",copy=False)
    supporting_documents_filename = fields.Char(string="Supporting Documents...")# field type converted in many2one to Char
    supporting_documents = fields.Binary(string="Supporting Documents" ,copy=False)
    join_date = fields.Date("Joining Date")
    end_date = fields.Date("Ending Date")
    company_type = fields.Selection(selection_add=[('faculty', 'Faculty')],ondelete={'faculty': 'cascade'})
    employee_id = fields.Many2one('hr.employee',string="Employees ")

    @api.model_create_multi
    def create(self, vals):
        res = super(Faculty, self).create(vals)
        for fac_rec in res:
            if fac_rec.company_type == 'faculty':
                fac_rec.faculty_id = self.env['ir.sequence'].next_by_code(
                    'faculty.seq')
            # res.employee_id = self.env['hr.employee'].create({'name':res.name,'job_title':'Faculty','job_id':res.job_id.id})
        return res

    def get_years():
        year_list = []
        for i in range(2016, 2036):
            year_list.append((i, str(i)))
        return year_list

    @api.onchange('company_type')
    def onchange_company_type(self):
        self.is_student = (self.company_type == 'student')
        self.is_faculty = (self.company_type == 'faculty')
        self.is_company = (self.company_type == 'company')


    @api.onchange('is_faculty')
    def onchange_company_type1(self):
        super(Faculty, self).onchange_company_type()
        if self.is_faculty == True:
            self.company_type = 'faculty'
            
    def _write_company_type(self):
        for partner in self:
            partner.is_company = partner.company_type == 'company'
            partner.is_student = partner.company_type == 'student'
            partner.is_faculty = partner.company_type == 'faculty'

    def _compute_company_type(self):
        for partner in self:
            if partner.is_student:
                partner.company_type = 'student'
            elif partner.is_faculty:
                partner.company_type = 'faculty'
            elif partner.is_company:
                partner.company_type = 'company'
            else:
                partner.company_type = 'person'

    @api.model
    def default_get(self, fields):
        res = super(Faculty, self).default_get(fields)
        if self._context.get('is_faculty') == True:
            res.update({'is_faculty': True})
        return res

# class Attachment(models.Model):
#   _inherit = 'ir.attachment'

#   attach_degree = fields.Many2many('res.partner', 'degree_attachment', 'attachment_id3', 'document_id',
#       string="Upload Degree", invisible=1 )
#   attach_doc = fields.Many2many('res.partner', 'supporting_documents', 'attachment_id3', 'document_id',
#       string="Supporting Documents", invisible=1 )

