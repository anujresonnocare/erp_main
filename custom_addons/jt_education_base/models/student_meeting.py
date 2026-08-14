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
from odoo import fields, models, api

class StudentMeeting(models.Model):

    _name = 'student.meeting'
    _description = 'Student Meeting'
    _rec_name = 'meeting_seq'

    _inherit = ['mail.thread', 'mail.activity.mixin']

    meeting_seq = fields.Char()
    topic = fields.Char(string="Topic")
    student_id = fields.Many2one('res.partner', string="Student")
    parent_id = fields.Many2one('res.partner', string="Parent")
    faculty_id = fields.Many2one('res.partner', string="Faculty")
    standard = fields.Many2one('student.standard', 'Standard', related="student_id.standard")
    note = fields.Html(string="Parents Feedback")
    note2 = fields.Html(string="Faculty Response and Evaluation")
    start_date = fields.Datetime(string='Start Date')
    end_date = fields.Datetime(string='End Date')
    state = fields.Selection(
        selection=[
            ('draft', 'New'),
            ('ongoing', 'Ongoing'),
            ('conducted', 'Conducted'),
            ('rescheduled', 'Rescheduled'),
            ('cancel', 'Cancelled'),
        ],
        string='Status',
        default='draft',
    )

    @api.model_create_multi
    def create(self, vals):
        res = super(StudentMeeting, self).create(vals)
        for meeting in res:
            meeting.meeting_seq = self.env['ir.sequence'].next_by_code(
                'studentmeetings.seq')
        return res

    def ongoing_meeting(self):
        self.state = 'ongoing'

    def conducted_meeting(self):
        self.state = 'conducted'

    def rescheduled_meeting(self):
        self.state = 'rescheduled'

    def cancel_meeting(self):
        self.state = 'cancel'

    def reset_to_draft(self):
        self.state = 'draft'