# -*- coding: utf-8 -*-
# from odoo import http


# class ReportCdtJourney(http.Controller):
#     @http.route('/report_cdt_journey/report_cdt_journey', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/report_cdt_journey/report_cdt_journey/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('report_cdt_journey.listing', {
#             'root': '/report_cdt_journey/report_cdt_journey',
#             'objects': http.request.env['report_cdt_journey.report_cdt_journey'].search([]),
#         })

#     @http.route('/report_cdt_journey/report_cdt_journey/objects/<model("report_cdt_journey.report_cdt_journey"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('report_cdt_journey.object', {
#             'object': obj
#         })

