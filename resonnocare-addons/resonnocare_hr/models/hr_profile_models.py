from odoo import models, fields


class ResonnocareHrEducation(models.Model):
    _name = "resonnocare.hr.education"
    _description = "Employee Education History"

    employee_id = fields.Many2one("hr.employee", string="Employee", ondelete="cascade", required=True)
    degree = fields.Char(string="Degree / Certification", required=True)
    specialization = fields.Char(string="Specialization / Major")
    university = fields.Char(string="University / Institute", required=True)
    year_of_passing = fields.Integer(string="Year of Passing")
    score = fields.Char(string="Percentage / CGPA")
    mode = fields.Selection([
        ('regular', 'Regular'),
        ('distance', 'Distance'),
        ('online', 'Online')
    ], string="Mode", default='regular')
    certificate = fields.Binary(string="Attach Certificate")
    certificate_filename = fields.Char(string="Certificate Filename")


class ResonnocareHrExperience(models.Model):
    _name = "resonnocare.hr.experience"
    _description = "Employee Employment History"

    employee_id = fields.Many2one("hr.employee", string="Employee", ondelete="cascade", required=True)
    company_name = fields.Char(string="Company Name", required=True)
    designation = fields.Char(string="Designation", required=True)
    department = fields.Char(string="Department / Function")
    employment_type = fields.Selection([
        ('permanent', 'Permanent'),
        ('contract', 'Contract'),
        ('trainee', 'Trainee')
    ], string="Employment Type", default='permanent')
    location = fields.Char(string="Location")
    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date")
    ctc_at_exit = fields.Char(string="CTC at Exit")
    reason_for_leaving = fields.Text(string="Reason for Leaving")
    reporting_manager = fields.Char(string="Reporting Manager Name & Contact")
    relieving_letter = fields.Binary(string="Upload Relieving Letter")
    relieving_letter_filename = fields.Char(string="Relieving Letter Filename")
    experience_letter = fields.Binary(string="Upload Experience Letter")
    experience_letter_filename = fields.Char(string="Experience Letter Filename")


class ResonnocareHrLicense(models.Model):
    _name = "resonnocare.hr.license"
    _description = "Employee Professional License / Registration"

    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        ondelete="cascade",
        required=True,
    )
    name = fields.Char(string="License Name", required=True)
    license_number = fields.Char(string="License / Registration Number", required=True)
    issuing_authority = fields.Char(string="Issuing Authority")
    validity_start = fields.Date(string="Validity Start")
    validity_end = fields.Date(string="Validity End")
    document = fields.Binary(string="Upload Document")
    document_filename = fields.Char(string="Document Filename")


class ResonnocareHrDependent(models.Model):
    _name = "resonnocare.hr.dependent"
    _description = "Employee Dependents for Mediclaim"
    _order = "id desc"

    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        ondelete="cascade",
        required=True,
    )
    name = fields.Char(string="Dependent Name", required=True)
    date_of_birth = fields.Date(string="Date of Birth", required=True)
    relation = fields.Selection(
        [
            ("spouse", "Spouse"),
            ("son", "Son"),
            ("daughter", "Daughter"),
            ("father", "Father"),
            ("mother", "Mother"),
            ("other", "Other"),
        ],
        string="Relation",
        required=True,
    )
