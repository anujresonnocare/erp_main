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
{
    'name': "Student Management",
    'sequence':1,
    'summary': "Manage the students details",
    'category': 'Student Extension',
    'version': '18.0.1.0.3',
    'depends': ['contacts','hr_recruitment'],
    'data': [
        'security/base_security.xml',
        'security/ir.model.access.csv',
        'data/confirm_student.xml',
        'demo/demo.xml',
        'views/student_view.xml',
        'views/district_view.xml',
        'views/village_view.xml',
        'views/province_view.xml',
        'views/student_standard_view.xml',
        'views/faculty_view.xml',
        'views/parent_view.xml',
        'views/how_know.xml',
        'wizard/student_transfer_wizard_view.xml',
        'views/action_and_menu.xml',
        'views/sequence.xml',
        'views/admission_inq_view.xml',
        'views/admission_cancellation_template.xml',
        'views/admission_successfull_template.xml',
        'views/admission_pending_fees_template.xml',
        'views/medium_view.xml',
        'views/board_view.xml',
        'views/student_meeting_view.xml',
        'views/res_company_view.xml',
        'views/res_config_settings_view.xml',
        'reports/student_certificate_report.xml'
        # 'wizard/change_academic_year_wizard.xml'
    ],
    'application': True,
    'license':'OPL-1',
}
