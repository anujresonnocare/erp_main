# -*- coding: utf-8 -*-
# from odoo import http


# class ResonnocarePatientReport(http.Controller):
#     @http.route('/resonnocare_patient_report/resonnocare_patient_report', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/resonnocare_patient_report/resonnocare_patient_report/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('resonnocare_patient_report.listing', {
#             'root': '/resonnocare_patient_report/resonnocare_patient_report',
#             'objects': http.request.env['resonnocare_patient_report.resonnocare_patient_report'].search([]),
#         })

#     @http.route('/resonnocare_patient_report/resonnocare_patient_report/objects/<model("resonnocare_patient_report.resonnocare_patient_report"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('resonnocare_patient_report.object', {
#             'object': obj
#         })

