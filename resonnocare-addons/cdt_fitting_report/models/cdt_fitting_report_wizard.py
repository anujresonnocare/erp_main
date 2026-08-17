# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date
from dateutil.relativedelta import relativedelta
import io, base64, xlsxwriter

class CdtFittingReportWizard(models.TransientModel):
    _name = 'cdt.fitting.report.wizard'
    _description = 'CDT Fitting Report Wizard'

    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)
    report_type = fields.Selection([
        ('ytd', 'Year to Date'), ('mtd', 'Month to Date'), 
        ('wtd', 'Week to Date'), ('yday', 'Yesterday'), ('custom', 'Custom Range')
    ], string='Report Type', default='ytd', required=True)
    area_manager_id = fields.Many2one('res.users', string='Area Manager')
    region = fields.Char(string='Region')
    clinic_ids = fields.Many2many('resonnocare.clinic', string='Clinics')
    report_format = fields.Selection([
        ('excel', 'Excel'), ('pdf', 'PDF'), ('both', 'Both')
    ], string='Report Format', default='excel', required=True)
    file_name = fields.Char(string='File Name', default='CDT_Fitting_Report')

    @api.onchange('report_type')
    def _onchange_report_type(self):
        today = fields.Date.today()
        if self.report_type == 'ytd':
            self.date_from = date(today.year, 1, 1)
            self.date_to = today
        elif self.report_type == 'mtd':
            self.date_from = date(today.year, today.month, 1)
            self.date_to = today
        elif self.report_type == 'wtd':
            monday = today - relativedelta(days=today.weekday())
            self.date_from = monday
            self.date_to = today
        elif self.report_type == 'yday':
            yesterday = today - relativedelta(days=1)
            self.date_from = yesterday
            self.date_to = yesterday
        else:
            self.date_from = False
            self.date_to = False

    def generate_report(self):
        self.ensure_one()
        if self.report_format in ['excel', 'both']:
            return self._generate_excel_report()
        return False

    def _get_report_data(self):
        report_obj = self.env['cdt.fitting.report']
        domain = [
            ('date_from', '=', self.date_from),
            ('date_to', '=', self.date_to),
            ('report_type', '=', self.report_type)
        ]
        if self.area_manager_id:
            domain.append(('area_manager_id', '=', self.area_manager_id.id))
        if self.region:
            domain.append(('region', '=', self.region))
        if self.clinic_ids:
            domain.append(('clinic_id', 'in', self.clinic_ids.ids))
        
        records = report_obj.search(domain, order='is_total_row desc, fitting_date desc')
        if not records:
            report_obj.search([])._generate_report_data(self.date_from, self.date_to, self.report_type)
            records = report_obj.search(domain, order='is_total_row desc, fitting_date desc')
        return records

    def _get_selection_dict(self, model, field_name):
        """Get selection dictionary from a field"""
        field = model._fields[field_name]
        selection = field.selection
        
        if callable(selection):
            # Odoo 18: selection is a lambda that takes model as argument
            try:
                result = selection(model)
                if result:
                    return dict(result)
            except (TypeError, ValueError):
                pass
            
            # Try with no arguments
            try:
                result = selection()
                if result:
                    return dict(result)
            except (TypeError, ValueError):
                pass
            
            # Try with field
            try:
                result = selection(field)
                if result:
                    return dict(result)
            except (TypeError, ValueError):
                pass
            
            return {}
        
        return dict(selection) if selection else {}

    def _generate_excel_report(self):
        records = self._get_report_data()
        if not records:
            raise ValidationError(_('No data found.'))
        
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        
        header_format = workbook.add_format({
            'bold': True, 'text_wrap': True, 'valign': 'top', 'align': 'center',
            'fg_color': '#D9E1F2', 'border': 1, 'font_size': 11
        })
        total_format = workbook.add_format({
            'bold': True, 'text_wrap': True, 'valign': 'top', 'align': 'center',
            'fg_color': '#E2EFDA', 'border': 1, 'font_size': 11
        })
        region_total_format = workbook.add_format({
            'bold': True, 'text_wrap': True, 'valign': 'top', 'align': 'center',
            'fg_color': '#DAEEF3', 'border': 1, 'font_size': 11
        })
        number_format = workbook.add_format({'num_format': '#,##0', 'border': 1, 'font_size': 10})
        currency_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1, 'font_size': 10})
        text_format = workbook.add_format({'border': 1, 'font_size': 10, 'text_wrap': True})
        title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter'})
        date_format = workbook.add_format({'border': 1, 'font_size': 10, 'num_format': 'dd-mmm-yyyy'})
        percent_format = workbook.add_format({'num_format': '0.00%', 'border': 1, 'font_size': 10})
        
        # ========================================
        # APPOINTMENT STATUS COLOR FORMATS
        # ========================================
        status_formats = {
            'draft': workbook.add_format({'border': 1, 'font_size': 10, 'fg_color': '#FFE4E1'}),      # Light Coral
            'scheduled': workbook.add_format({'border': 1, 'font_size': 10, 'fg_color': '#E0FFFF'}),   # Light Cyan
            'checked_in': workbook.add_format({'border': 1, 'font_size': 10, 'fg_color': '#FFFACD'}),  # Light Goldenrod
            'in_consultation': workbook.add_format({'border': 1, 'font_size': 10, 'fg_color': '#FFDAB9'}), # Peach Puff
            'completed': workbook.add_format({'border': 1, 'font_size': 10, 'fg_color': '#98FB98'}),  # Light Green
            'cancelled': workbook.add_format({'border': 1, 'font_size': 10, 'fg_color': '#FFC0C0'}),   # Light Pink
            'no_show': workbook.add_format({'border': 1, 'font_size': 10, 'fg_color': '#D3D3D3'}),     # Light Gray
        }
        
        # ========================================
        # STATUS MAP FOR DISPLAY
        # ========================================
        status_map = {
            'draft': 'Draft',
            'scheduled': 'Scheduled',
            'checked_in': 'Checked In',
            'in_consultation': 'In Consultation',
            'completed': 'Completed',
            'cancelled': 'Cancelled',
            'no_show': 'No Show'
        }
        
        sheet_name = self.report_type.upper()
        worksheet = workbook.add_worksheet(sheet_name)
        worksheet.merge_range('A1:U1', f'Fitting Report: {self.date_from.strftime("%d %b %Y")} To {self.date_to.strftime("%d %b %Y")}', title_format)
        
        # ========================================
        # HEADERS WITH STATUS AND SERIAL NUMBERS
        # ========================================
        headers = [
            ('Fitting Date', 14),
            ('Audiologist Name', 20),
            ('Client Code', 14),
            ('Name of Client', 25),
            ('Client Type', 14),
            ('Type of Hearing Equipment & Accessories', 35),
            ('Quantity', 10),
            ('MRP (Unit Price)', 16),
            ('Gross (Rs.)', 16),
            ('Discount (%)', 12),
            ('Discount Amount (Rs.)', 18),
            ('Total Amt. Receivable (Rs.)', 22),
            ('Clinic Name', 20),
            ('Cost Centre', 14),
            ('Weekly Target (Rs.)', 18),
            ('Region', 14),
            ('ABM', 18),
            ('Type of Clinic', 14),
            ('Status', 14),           # ← Appointment Status
            ('Serial Numbers', 25)    # ← Serial Numbers
        ]
        
        col = 0
        for header, width in headers:
            worksheet.write(1, col, header, header_format)
            worksheet.set_column(col, col, width)
            col += 1
        
        row = 2
        field_mapping = [
            'fitting_date',
            'audiologist_name',
            'client_code',
            'client_name',
            'client_type',
            'equipment_type',
            'quantity',
            'unit_price',
            'gross',
            'discount',
            'discount_amount',
            'total_amt_receivable',
            'clinic_name',
            'cost_centre',
            'weekly_target',
            'region',
            'area_manager_name',
            'clinic_type',
            'status',           # ← Appointment Status
            'serial_numbers'    # ← Serial Numbers
        ]
        
        # ========================================
        # GET SELECTION MAPS FOR DISPLAY
        # ========================================
        ReportModel = self.env['cdt.fitting.report']
        
        # Get client_type and clinic_type selection maps
        client_type_map = self._get_selection_dict(ReportModel, 'client_type')
        clinic_type_map = self._get_selection_dict(ReportModel, 'clinic_type')
        
        for record in records:
            row_format = region_total_format if record.is_region_total else total_format if record.is_area_manager_total else text_format
            
            col = 0
            for field_name in field_mapping:
                value = getattr(record, field_name, '') or ''
                
                if field_name == 'fitting_date' and value:
                    worksheet.write(row, col, value, date_format)
                elif field_name in ['quantity']:
                    worksheet.write(row, col, value or 0, number_format)
                elif field_name in ['unit_price', 'gross', 'discount_amount', 'total_amt_receivable', 'weekly_target']:
                    worksheet.write(row, col, value or 0, currency_format)
                elif field_name == 'discount':
                    worksheet.write(row, col, (value / 100) if value else 0, percent_format)
                elif field_name == 'client_type':
                    worksheet.write(row, col, client_type_map.get(value, value), row_format)
                elif field_name == 'clinic_type':
                    worksheet.write(row, col, clinic_type_map.get(value, value), row_format)
                elif field_name == 'status':
                    display_value = status_map.get(value, value)
                    status_format = status_formats.get(value, text_format)
                    worksheet.write(row, col, display_value, status_format)
                elif field_name == 'serial_numbers':
                    worksheet.write(row, col, value or '', row_format)
                else:
                    worksheet.write(row, col, value or '', row_format)
                col += 1
            row += 1
        
        workbook.close()
        file_data = output.getvalue()
        file_name = f"{self.file_name}_{self.report_type}_{self.date_from.strftime('%Y%m%d')}_{self.date_to.strftime('%Y%m%d')}.xlsx"
        file_data_base64 = base64.b64encode(file_data)
        attachment = self.env['ir.attachment'].create({
            'name': file_name, 'type': 'binary', 'datas': file_data_base64,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': 'cdt.fitting.report.wizard', 'res_id': self.id
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new'
        }