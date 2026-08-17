# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import logging
import io
import base64
import xlsxwriter

_logger = logging.getLogger(__name__)

class CdtJourneyReportWizard(models.TransientModel):
    _name = 'cdt.journey.report.wizard'
    _description = 'CDT Journey Report Wizard'

    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)
    report_type = fields.Selection([
        ('ytd', 'Year to Date'),
        ('mtd', 'Month to Date'),
        ('wtd', 'Week to Date'),
        ('yday', 'Yesterday'),
        ('custom', 'Custom Range')
    ], string='Report Type', default='ytd', required=True)
    area_manager_id = fields.Many2one('res.users', string='Area Manager')
    region = fields.Char(string='Region')
    clinic_ids = fields.Many2many('resonnocare.clinic', string='Clinics')
    report_format = fields.Selection([
        ('excel', 'Excel'),
        ('pdf', 'PDF'),
        ('both', 'Both')
    ], string='Report Format', default='excel', required=True)
    file_name = fields.Char(string='File Name', default='CDT_Journey_Report')

    @api.onchange('report_type')
    def _onchange_report_type(self):
        """Set default date range based on report type"""
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
        """Generate the report in selected format"""
        self.ensure_one()
        
        if self.report_format in ['excel', 'both']:
            return self._generate_excel_report()
        elif self.report_format == 'pdf':
            return self._generate_excel_report()
        return False

    def _get_report_data(self):
        """Get report data for the selected criteria"""
        report_obj = self.env['cdt.journey.report']
        
        # Search for existing report data
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
        
        # Get all records including totals
        records = report_obj.search(domain, order='is_total_row desc, area_manager_name, clinic_name')
        
        # If no records found, generate them first
        if not records:
            # Generate report data first
            report_obj.search([])._generate_report_data(
                self.date_from, 
                self.date_to, 
                self.report_type
            )
            records = report_obj.search(domain, order='is_total_row desc, area_manager_name, clinic_name')
        
        return records

    def _generate_excel_report(self):
        """Generate Excel report with all data matching the sample format"""
        records = self._get_report_data()
        
        if not records:
            raise ValidationError(_("No data found for the selected criteria."))
        
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        
        # ========================================
        # FORMATS WITH COLORS
        # ========================================
        
        # Section Header Format (Row 1) - Light Blue
        section_header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'align': 'center',
            'fg_color': '#D9E1F2',
            'border': 1,
            'font_size': 10
        })
        
        # Basic info headers (Store Name, StoreCode, etc.) - Light Blue
        basic_header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'align': 'center',
            'fg_color': '#D9E1F2',
            'border': 1,
            'font_size': 10
        })
        
        # Sky Blue - Ext. Dr., Ext. Dr. FUP, Int. Dr., Int. Dr. FUP
        sky_blue_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'align': 'center',
            'fg_color': '#87CEEB',  # Sky Blue
            'border': 1,
            'font_size': 10
        })
        
        # Light Green - Digital Marketing, Digital Marketing FUP, Camp with Doctor, Camp with RWA
        light_green_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'align': 'center',
            'fg_color': '#90EE90',  # Light Green
            'border': 1,
            'font_size': 10
        })
        
        # Light Yellow - OUTREACH, OUT-ACH, GP-ACH, OUT + GP FUP, Total
        light_yellow_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'align': 'center',
            'fg_color': '#FFFF99',  # Light Yellow
            'border': 1,
            'font_size': 10
        })
        
        # Light Pink - Renew
        light_pink_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'align': 'center',
            'fg_color': '#FFB6C1',  # Light Pink
            'border': 1,
            'font_size': 10
        })
        
        # Light Purple - OVERALL
        light_purple_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'align': 'center',
            'fg_color': '#D8BFD8',  # Light Purple
            'border': 1,
            'font_size': 10
        })
        
        # Sub-Sub Header Format - Light Yellow
        sub_sub_header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'align': 'center',
            'fg_color': '#FFFF99',  # Light Yellow
            'border': 1,
            'font_size': 9
        })
        
        total_format = workbook.add_format({
            'bold': True,
            'fg_color': '#E2EFDA',
            'border': 1,
            'font_size': 10
        })
        
        region_total_format = workbook.add_format({
            'bold': True,
            'fg_color': '#DAEEF3',
            'border': 1,
            'font_size': 10
        })
        
        number_format = workbook.add_format({
            'num_format': '#,##0',
            'border': 1,
            'font_size': 10
        })
        
        percent_format = workbook.add_format({
            'num_format': '0.00%',
            'border': 1,
            'font_size': 10
        })
        
        currency_format = workbook.add_format({
            'num_format': '#,##0.00',
            'border': 1,
            'font_size': 10
        })
        
        text_format = workbook.add_format({
            'border': 1,
            'font_size': 10,
            'text_wrap': True
        })
        
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 12,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        # ========================================
        # CREATE WORKSHEET
        # ========================================
        sheet_name = self.report_type.upper()
        worksheet = workbook.add_worksheet(sheet_name)
        
        # Row 0: Title
        worksheet.merge_range('A1:EY1', f'Date Range: {self.date_from.strftime("%d %b %Y")} To {self.date_to.strftime("%d %b %Y")}', title_format)
        
        # ========================================
        # ROW 1 (INDEX 1): SECTION HEADERS (MERGED CELLS)
        # ========================================
        sections = [
            (9, 22, 'TOTAL NUMBER OF APPOINTMENTS'),
            (23, 36, 'TOTAL NUMBER OF DIAGNOSTIC APPOINTMENTS'),
            (37, 50, 'HEARING TEST APPOINTMENTS BOOKED'),
            (51, 64, 'HEARING TEST APPOINTMENTS ATTENDED'),
            (65, 78, 'NET ATTENDANCE %'),
            (79, 92, 'HEARING TEST OPPORTUNITY (HEARING LOSS)'),
            (93, 106, 'Hearing Test Opportunity % (HL %)'),
            (107, 120, '# Conversions (Prescriptions)'),
            (121, 134, 'Conversion Rate %'),
            (135, 148, '# Binaural'),
            (149, 162, 'Binaural Rate %'),
            (163, 176, 'HA Units'),
            (177, 190, 'ASP'),
            (191, 204, 'Gross Revenue'),
            (205, 218, 'Fitting Revenue'),
        ]
        
        # First 9 columns are basic info (Store Name to Store Version)
        worksheet.merge_range(1, 0, 1, 8, '', section_header_format)
        
        # Write the section headers
        for start_col, end_col, section_name in sections:
            worksheet.merge_range(1, start_col, 1, end_col, section_name, section_header_format)
        
        # Last 2 columns (Opening Date, Closed Date)
        worksheet.merge_range(1, 219, 1, 220, '', section_header_format)
        
        # ========================================
        # ROW 2 (INDEX 2): SUB-HEADERS WITH COLORS
        # ========================================
        
        # First write all headers with their specific colors
        col = 0
        
        # Basic info (Store Name to Store Version) - Light Blue
        basic_headers = [
            ('Store Name', 25), ('StoreCode', 12), ('City', 12), ('State', 12),
            ('Area Manager', 18), ('Region', 12), ('Clinic Type', 10), ('Opening Date', 12),
            ('Store Version', 12)
        ]
        for header, width in basic_headers:
            worksheet.write(2, col, header, basic_header_format)
            worksheet.set_column(col, col, width)
            col += 1
        
        # For each section (15 sections)
        for section_num in range(15):
            # Sky Blue - Ext. Dr., Ext. Dr. FUP, Int. Dr., Int. Dr. FUP
            worksheet.write(2, col, 'Ext. Dr.', sky_blue_format)
            worksheet.set_column(col, col, 10)
            col += 1
            worksheet.write(2, col, 'Ext. Dr. FUP', sky_blue_format)
            worksheet.set_column(col, col, 10)
            col += 1
            worksheet.write(2, col, 'Int. Dr.', sky_blue_format)
            worksheet.set_column(col, col, 10)
            col += 1
            worksheet.write(2, col, 'Int. Dr. FUP', sky_blue_format)
            worksheet.set_column(col, col, 10)
            col += 1
            
            # Light Green - Digital Marketing, Digital Marketing FUP, Camp with Doctor, Camp with RWA
            worksheet.write(2, col, 'Digital Marketing', light_green_format)
            worksheet.set_column(col, col, 12)
            col += 1
            worksheet.write(2, col, 'Digital Marketing FUP', light_green_format)
            worksheet.set_column(col, col, 12)
            col += 1
            worksheet.write(2, col, 'Camp with Doctor', light_green_format)
            worksheet.set_column(col, col, 12)
            col += 1
            worksheet.write(2, col, 'Camp with RWA', light_green_format)
            worksheet.set_column(col, col, 10)
            col += 1
            
            # Light Yellow - OUTREACH
            worksheet.write(2, col, 'OUTREACH', light_yellow_format)
            worksheet.set_column(col, col, 10)
            col += 1
            
            # Blank columns (3 blank columns) - No color
            worksheet.write(2, col, '', text_format)
            worksheet.set_column(col, col, 10)
            col += 1
            worksheet.write(2, col, '', text_format)
            worksheet.set_column(col, col, 10)
            col += 1
            worksheet.write(2, col, '', text_format)
            worksheet.set_column(col, col, 10)
            col += 1
            
            # Light Pink - Renew
            worksheet.write(2, col, 'Renew', light_pink_format)
            worksheet.set_column(col, col, 8)
            col += 1
            
            # Light Purple - OVERALL
            worksheet.write(2, col, 'OVERALL', light_purple_format)
            worksheet.set_column(col, col, 10)
            col += 1
        
        # Last 2 columns (Opening Date, Closed Date) - Light Blue
        worksheet.write(2, col, 'Opening Date', basic_header_format)
        worksheet.set_column(col, col, 12)
        col += 1
        worksheet.write(2, col, 'Closed Date', basic_header_format)
        worksheet.set_column(col, col, 12)
        col += 1
        
        # ========================================
        # ROW 3 (INDEX 3): SUB-SUB HEADERS (OUT-ACH, GP-ACH, OUT + GP FUP, Total) - Light Yellow
        # ========================================
        for section_start in [9, 23, 37, 51, 65, 79, 93, 107, 121, 135, 149, 163, 177, 191, 205]:
            out_ach_col = section_start + 8
            worksheet.write(3, out_ach_col, 'OUT-ACH', sub_sub_header_format)
            worksheet.write(3, out_ach_col + 1, 'GP-ACH', sub_sub_header_format)
            worksheet.write(3, out_ach_col + 2, 'OUT + GP  FUP', sub_sub_header_format)
            worksheet.write(3, out_ach_col + 3, 'Total', sub_sub_header_format)
        
        # ========================================
        # DEFINE FIELD MAPPINGS FOR EACH SECTION
        # ========================================
        def get_section_fields(section_prefix, overall_field):
            """Get field list for a section"""
            return [
                f'{section_prefix}_ext_dr_appointments',
                f'{section_prefix}_ext_dr_fup_appointments',
                f'{section_prefix}_int_dr_appointments',
                f'{section_prefix}_int_dr_fup_appointments',
                f'{section_prefix}_digital_marketing_appointments',
                f'{section_prefix}_digital_marketing_fup_appointments',
                f'{section_prefix}_camp_doctor_appointments',
                f'{section_prefix}_camp_rwa_appointments',
                f'{section_prefix}_outreach_appointments',
                None,  # Blank column
                None,  # Blank column
                None,  # Blank column
                f'{section_prefix}_renew_appointments',
                overall_field
            ]
        
        sections_config = [
            ('ta', 'total_appointments'),
            ('da', 'total_diagnostic_appointments'),
            ('htb', 'hearing_test_booked'),
            ('hta', 'hearing_test_attended'),
            ('nap', 'net_attendance_percent'),
            ('hto', 'hearing_test_opportunity'),
            ('htop', 'hearing_test_opportunity_percentage'),
            ('cp', 'conversions_prescriptions'),
            ('crp', 'conversion_rate_percent'),
            ('bin', 'binaural'),
            ('brp', 'binaural_rate_percentage'),
            ('ha', 'hearing_unit'),
            ('asp', 'average_selling_price'),
            ('gr', 'gross_revenue'),
            ('fr', 'fitting_revenue'),
        ]
        
        # Build complete field list
        field_list = [
            'clinic_name', 'clinic_code', 'city', 'state', 'area_manager_name',
            'region', 'clinic_type', 'opening_date', None,  # Store Version (blank)
        ]
        
        for section_prefix, overall_field in sections_config:
            section_fields = get_section_fields(section_prefix, overall_field)
            field_list.extend(section_fields)
        
        field_list.extend(['opening_date', None])  # Closing dates
        
        # ========================================
        # WRITE DATA ROWS
        # ========================================
        row = 4  # Start from row 5
        
        for record in records:
            row_format = text_format
            if hasattr(record, 'is_region_total') and record.is_region_total:
                row_format = region_total_format
            elif hasattr(record, 'is_area_manager_total') and record.is_area_manager_total:
                row_format = total_format
            
            col = 0
            for field_name in field_list:
                if field_name is None:
                    worksheet.write(row, col, '', row_format)
                    col += 1
                    continue
                
                value = getattr(record, field_name, 0) or 0
                
                # Determine format based on field type
                if field_name in ['net_attendance_percent', 'hearing_test_opportunity_percentage',
                                    'conversion_rate_percent', 'binaural_rate_percentage'] or \
                    field_name.startswith('nap_') or field_name.startswith('htop_') or \
                    field_name.startswith('crp_') or field_name.startswith('brp_'):
                    # Percentage fields
                    worksheet.write(row, col, value / 100 if value else 0, percent_format)
                elif field_name in ['average_selling_price', 'gross_revenue', 'fitting_revenue'] or \
                        field_name.startswith('asp_') or field_name.startswith('gr_') or \
                        field_name.startswith('fr_') or field_name.startswith('fitting_'):
                    # Currency fields
                    worksheet.write(row, col, value, currency_format)
                elif field_name in ['opening_date']:
                    # Date fields
                    worksheet.write(row, col, value, text_format)
                else:
                    # Number fields
                    worksheet.write(row, col, value, number_format)
                
                col += 1
            
            row += 1
        
        workbook.close()
        
        # Create attachment
        file_data = output.getvalue()
        file_name = f"{self.file_name}_{self.report_type}_{self.date_from.strftime('%Y%m%d')}_{self.date_to.strftime('%Y%m%d')}.xlsx"
        file_data_base64 = base64.b64encode(file_data)
        
        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'type': 'binary',
            'datas': file_data_base64,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': 'cdt.journey.report.wizard',
            'res_id': self.id,
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }