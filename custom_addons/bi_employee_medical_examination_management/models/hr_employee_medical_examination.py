# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError



class HREmployeeMedicalExamination(models.Model):
    _name = "hr.employee.medical.examination"
    _description = "HR Employee Medical Examination"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'employee_id'

    state = fields.Selection([
        ("pending", "Pending"),
        ("done", "Done"),
        ("cancelled", "Cancelled"),
        ("rejected", "Rejected")], default="pending", readonly=True, tracking=True)
    date = fields.Date(string="Examination Date", tracking=True)
    result = fields.Selection([
        ("failed", "Failed"),
        ("passed", "Passed")], default='passed', tracking=True)
    employee_id = fields.Many2one("hr.employee", string="Employee", required=True, tracking=True)
    note = fields.Text('Notes', tracking=True)
    next_examination_date = fields.Date(string="Next Examination Date", tracking=True)
    before_days = fields.Integer(string="Days", help="How many number of days before to get the notification email")
    notification_type = fields.Selection([
        ('single', 'Notification on expiry date'),
        ('multi', 'Notification before few days'),
        ('everyday', 'Everyday till expiry date'),
        ('everyday_after', 'Notification on and after expiry')
    ], string='Notification Type',  default='single',
        help="""
               Notification on expiry date: You will get notification only on expiry date.
               Notification before few days: You will get notification in 2 days.On expiry date and number of days before date.
               Everyday till expiry date: You will get notification from number of days till the expiry date of the document.
               Notification on and after expiry: You will get notification on the expiry date and continues upto Days.
               If you did't select any then you will get notification before 7 days of document expiry.""")

    @api.constrains('date', 'next_examination_date')
    def _check_dates(self):
        now = datetime.now()
        date_now = now.date()
        for record in self:
            if record.date and record.next_examination_date:
                if record.next_examination_date < record.date:
                    raise ValidationError("Next Examination Date must be greater than Examination Date!")
            if date_now > record.date:
                raise ValidationError("Invalid Date Formate !")

    def back_to_pending(self):
        self.write({"state": "pending"})

    def to_done(self):
        self.write({"state": "done"})

    def to_cancelled(self):
        self.write({"state": "cancelled"})

    def to_rejected(self):
        self.write({"state": "rejected"})

    @api.onchange('notification_type')
    def onchange_notification_type(self):
        for rec in self:
            if rec.notification_type == "single" or rec.notification_type == "everyday":
                rec.before_days = False

    def cron_next_medical_examination(self):
        now = datetime.now() + timedelta(days=0)
        date_now = now.date()
        examinations = self.search([])
        for examination in examinations:
            if examination.next_examination_date:
                if examination.notification_type == 'single':
                    exp_date = fields.Date.from_string(examination.next_examination_date)
                    if date_now == exp_date:
                        mail_content = "  Hello  " + examination.employee_id.name + ",<br>Your Medical Examination " + examination.note + " due date is " + \
                                       str(examination.next_examination_date) + ". Please done your medical examination before it."
                        main_content = {
                            'subject': _('Next Medical Examination on %s') % examination.next_examination_date,
                            'author_id': self.env.user.id,
                            'body_html': mail_content,
                            'email_to': examination.employee_id.work_email,
                        }
                        self.env['mail.mail'].create(main_content).send()
                elif examination.notification_type == 'multi':
                    exp_date = fields.Date.from_string(examination.next_examination_date) - timedelta(days=examination.before_days)
                    if date_now == exp_date or date_now == examination.next_examination_date:
                        mail_content = "  Hello  " + examination.employee_id.name + ",<br>Your Medical Examination " + examination.note + " due date is " + \
                                       str(examination.next_examination_date) + ". Please done your medical examination before it."
                        main_content = {
                            'subject': _('Next Medical Examination on %s') % examination.next_examination_date,
                            'author_id': self.env.user.id,
                            'body_html': mail_content,
                            'email_to': examination.employee_id.work_email,
                        }
                        self.env['mail.mail'].create(main_content).send()
                elif examination.notification_type == 'everyday':
                    exp_date = fields.Date.from_string(examination.next_examination_date)- timedelta(days=examination.before_days)
                    if date_now <= exp_date or date_now <= examination.next_examination_date:
                        mail_content = "  Hello  " + examination.employee_id.name + ",<br>Your Medical Examination " + examination.note + " due date is " + \
                                       str(examination.next_examination_date) + ". Please done your medical examination before it."
                        main_content = {
                            'subject': _('Next Medical Examination on %s') % examination.next_examination_date,
                            'author_id': self.env.user.id,
                            'body_html': mail_content,
                            'email_to': examination.employee_id.work_email,
                        }
                        self.env['mail.mail'].create(main_content).send()

                elif examination.notification_type == 'everyday_after':
                    exp_date = fields.Date.from_string(examination.next_examination_date) + timedelta(days=examination.before_days)
                    if date_now == exp_date or date_now == examination.next_examination_date:
                        mail_content = "  Hello  " + examination.employee_id.name + ",<br>Your Medical Examination " + examination.note + " due date is " + \
                                       str(examination.next_examination_date) + ". Please done your medical examination before it."
                        main_content = {
                            'subject': _('Next Medical Examination on %s') % examination.next_examination_date,
                            'author_id': self.env.user.id,
                            'body_html': mail_content,
                            'email_to': examination.employee_id.work_email,
                        }
                        self.env['mail.mail'].create(main_content).send()
                else:
                    exp_date = fields.Date.from_string(examination.next_examination_date) - timedelta(days=7)
                    if date_now >= exp_date:
                        mail_content = "  Hello  " + examination.employee_id.name + ",<br>Your Medical Examination " + examination.note + " due date is " + \
                                       str(examination.next_examination_date) + ". Please done your medical examination before it."
                        main_content = {
                            'subject': _('Next Medical Examination on %s') % examination.next_examination_date,
                            'author_id': self.env.user.id,
                            'body_html': mail_content,
                            'email_to': examination.employee_id.work_email,
                        }
                        self.env['mail.mail'].create(main_content).send()



