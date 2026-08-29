# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
import io
import base64
import xlsxwriter
import logging

_logger = logging.getLogger(__name__)

class DailyPrescriptionReportWizard(models.TransientModel):
    _name = 'daily.prescription.report.wizard'
    _description = 'Daily Prescription Report Wizard'

    # ========================================
    # WIZARD FIELDS
    # ========================================
    area_manager_id = fields.Many2one('res.users', string='Area Manager')
    region = fields.Char(string='Region')
    clinic_ids = fields.Many2many('resonnocare.clinic', string='Clinics')
    file_name = fields.Char(string='File Name', default='Daily_Prescription_Report')

    def print_report(self):
        """Generate and download the Excel report with all sheets"""
        self.ensure_one()
        return self._generate_excel_report()

    def _get_date_ranges(self):
        """Get all date ranges for YTD, MTD, WTD, Yesterday"""
        today = fields.Date.today()
        date_ranges = {}
        
        # YTD - Indian Financial Year (April 1 to current date)
        if today.month >= 4:
            ytd_from = date(today.year, 4, 1)
        else:
            ytd_from = date(today.year - 1, 4, 1)
        date_ranges['ytd'] = {
            'label': 'Year to Date (Financial Year)',
            'date_from': ytd_from,
            'date_to': today
        }
        
        # MTD - Month to Date
        date_ranges['mtd'] = {
            'label': 'Month to Date',
            'date_from': date(today.year, today.month, 1),
            'date_to': today
        }
        
        # WTD - Week to Date (Monday to Sunday of current week)
        # Get Monday of current week
        monday = today - timedelta(days=today.weekday())
        # Get Sunday of current week
        sunday = monday + timedelta(days=6)
        # If today is before Sunday, use today as end date
        if today <= sunday:
            wtd_to = today
        else:
            wtd_to = sunday
        date_ranges['wtd'] = {
            'label': 'Week to Date (Monday - Sunday)',
            'date_from': monday,
            'date_to': wtd_to
        }
        
        # Yesterday
        yesterday = today - timedelta(days=1)
        date_ranges['yday'] = {
            'label': 'Yesterday',
            'date_from': yesterday,
            'date_to': yesterday
        }
        
        return date_ranges

    def _get_appointments_for_date_range(self, date_from, date_to, filters=None):
        """Fetch appointments for a specific date range"""
        # Get DEVICE appointment types only
        device_appointment_types = self.env['resonnocare.appointment.type'].search([
            ('sale_type', '=', 'device')
        ])
        
        if not device_appointment_types:
            _logger.warning("No device appointment types found")
            return self.env['resonnocare.appointment']
        
        domain = [
            ('appointment_date', '>=', date_from),
            ('appointment_date', '<=', date_to),
            ('status', '=', 'completed'),
            ('appointment_type_id', 'in', device_appointment_types.ids)
        ]
        
        if filters:
            if filters.get('area_manager_id'):
                domain.append(('clinic_id.area_manager_id', '=', filters['area_manager_id'].id))
            if filters.get('region'):
                domain.append(('clinic_id.region', '=', filters['region']))
            if filters.get('clinic_ids'):
                domain.append(('clinic_id', 'in', filters['clinic_ids'].ids))
        
        appointments = self.env['resonnocare.appointment'].search(domain)
        _logger.info("Found %s appointments for date range %s to %s", len(appointments), date_from, date_to)
        return appointments

    def _compute_prescription_metrics(self, appointment, sale_order, sale_line):
        """Compute prescription metrics for a sale order line"""
        vals = {}
        vals['clinic_name'] = appointment.clinic_id.name
        vals['patient_name'] = appointment.patient_id.name if appointment.patient_id else ''
        vals['region'] = appointment.clinic_id.region
        vals['area_manager_name'] = appointment.clinic_id.area_manager_id.name if appointment.clinic_id.area_manager_id else ''
        vals['prescription_date'] = appointment.appointment_date
        vals['audiologist_name'] = appointment.audiologist_id.name if appointment.audiologist_id else ''
        vals['appointment_type'] = appointment.appointment_type_id.name if appointment.appointment_type_id else ''
        
        # Product/Equipment details
        vals['product_description'] = sale_line.product_id.name or 'Hearing Aid'
        vals['item_style'] = sale_line.product_id.product_tmpl_id.item_style or ''
        vals['quantity'] = int(sale_line.product_uom_qty) if sale_line.product_uom_qty else 1
        
        # Pricing details
        unit_price = sale_line.price_unit or sale_line.product_id.lst_price or 0.0
        vals['unit_price'] = unit_price
        
        discount_percentage = sale_line.discount or 0.0
        vals['discount'] = discount_percentage
        
        subtotal = unit_price * vals['quantity']
        discount_amount = subtotal * (discount_percentage / 100)
        vals['discount_amount'] = discount_amount
        vals['net_prescription_value'] = subtotal - discount_amount
        
        return vals

    def _calculate_totals(self, data_rows):
        """Calculate totals for numeric fields"""
        totals = {
            'quantity': 0,
            'unit_price': 0,
            'discount_amount': 0,
            'net_prescription_value': 0
        }
        
        for row in data_rows:
            totals['quantity'] += row.get('quantity', 0)
            totals['unit_price'] += row.get('unit_price', 0)
            totals['discount_amount'] += row.get('discount_amount', 0)
            totals['net_prescription_value'] += row.get('net_prescription_value', 0)
        
        return totals

    def _calculate_area_manager_totals(self, report_data):
        """Calculate area manager totals"""
        area_manager_totals = {}
        for row in report_data:
            am_name = row.get('area_manager_name', '')
            if am_name:
                if am_name not in area_manager_totals:
                    area_manager_totals[am_name] = {
                        'quantity': 0,
                        'discount_amount': 0,
                        'net_prescription_value': 0
                    }
                area_manager_totals[am_name]['quantity'] += row.get('quantity', 0)
                area_manager_totals[am_name]['discount_amount'] += row.get('discount_amount', 0)
                area_manager_totals[am_name]['net_prescription_value'] += row.get('net_prescription_value', 0)
        return area_manager_totals

    def _calculate_region_totals(self, report_data):
        """Calculate region totals"""
        region_totals = {}
        for row in report_data:
            region = row.get('region', '')
            if region:
                if region not in region_totals:
                    region_totals[region] = {
                        'quantity': 0,
                        'discount_amount': 0,
                        'net_prescription_value': 0
                    }
                region_totals[region]['quantity'] += row.get('quantity', 0)
                region_totals[region]['discount_amount'] += row.get('discount_amount', 0)
                region_totals[region]['net_prescription_value'] += row.get('net_prescription_value', 0)
        return region_totals

    def _write_sheet_data(self, workbook, worksheet, report_data, date_from, date_to, sheet_title):
        """Write data to a worksheet"""
        
        # ========================================
        # FORMAT DEFINITIONS
        # ========================================
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'align': 'center',
            'fg_color': '#D9E1F2',
            'border': 1,
            'font_size': 11
        })
        total_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'align': 'center',
            'fg_color': '#E2EFDA',
            'border': 1,
            'font_size': 11
        })
        area_manager_total_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'align': 'center',
            'fg_color': '#DAEEF3',
            'border': 1,
            'font_size': 11
        })
        region_total_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'align': 'center',
            'fg_color': '#FFF2CC',
            'border': 1,
            'font_size': 11
        })
        number_format = workbook.add_format({
            'num_format': '#,##0',
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
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter'
        })
        date_format = workbook.add_format({
            'border': 1,
            'font_size': 10,
            'num_format': 'dd-mmm-yyyy'
        })
        percent_format = workbook.add_format({
            'num_format': '0.00%',
            'border': 1,
            'font_size': 10
        })
        
        # Title
        worksheet.merge_range('A1:O1', 
            f'{sheet_title}: {date_from.strftime("%d %b %Y")} To {date_to.strftime("%d %b %Y")}', 
            title_format)
        
        # ========================================
        # HEADERS
        # ========================================
        headers = [
            ('S.No', 6),
            ('Date', 14),
            ('Clinic Name', 30),
            ('Patient Name', 25),
            ('Audiologist', 22),
            ('Area Manager', 22),
            ('Region', 14),
            ('Appointment Type', 20),
            ('Product Description', 35),
            ('Item Style', 20),
            ('Quantity', 10),
            ('MRP (Unit Price)', 16),
            ('Discount (%)', 12),
            ('Discount Amount', 16),
            ('Net Prescription Value', 22)
        ]
        
        col = 0
        for header, width in headers:
            worksheet.write(1, col, header, header_format)
            worksheet.set_column(col, col, width)
            col += 1
        
        # ========================================
        # WRITE DATA ROWS
        # ========================================
        row = 2
        serial_no = 1
        
        for data in report_data:
            worksheet.write(row, 0, serial_no, text_format)
            serial_no += 1
            
            worksheet.write(row, 1, data.get('prescription_date'), date_format)
            worksheet.write(row, 2, data.get('clinic_name') or '', text_format)
            worksheet.write(row, 3, data.get('patient_name') or '', text_format)
            worksheet.write(row, 4, data.get('audiologist_name') or '', text_format)
            worksheet.write(row, 5, data.get('area_manager_name') or '', text_format)
            worksheet.write(row, 6, data.get('region') or '', text_format)
            worksheet.write(row, 7, data.get('appointment_type') or '', text_format)
            worksheet.write(row, 8, data.get('product_description') or '', text_format)
            worksheet.write(row, 9, data.get('item_style') or '', text_format)
            worksheet.write(row, 10, data.get('quantity') or 0, number_format)
            worksheet.write(row, 11, data.get('unit_price') or 0, currency_format)
            worksheet.write(row, 12, (data.get('discount') or 0) / 100, percent_format)
            worksheet.write(row, 13, data.get('discount_amount') or 0, currency_format)
            worksheet.write(row, 14, data.get('net_prescription_value') or 0, currency_format)
            row += 1
        
        # Calculate totals
        region_totals = self._calculate_region_totals(report_data)
        area_manager_totals = self._calculate_area_manager_totals(report_data)
        grand_total = self._calculate_totals(report_data)
        
        # ========================================
        # ADD REGION TOTALS
        # ========================================
        if region_totals:
            row += 1
            worksheet.merge_range(row, 0, row, 14, 'REGION TOTALS', total_format)
            row += 1
            
            for region, totals in region_totals.items():
                worksheet.write(row, 0, '', text_format)
                worksheet.write(row, 1, '', text_format)
                worksheet.write(row, 2, '', text_format)
                worksheet.write(row, 3, '', text_format)
                worksheet.write(row, 4, '', text_format)
                worksheet.write(row, 5, '', text_format)
                worksheet.write(row, 6, region, region_total_format)
                worksheet.write(row, 7, '', text_format)
                worksheet.write(row, 8, 'Total', region_total_format)
                worksheet.write(row, 9, '', text_format)
                worksheet.write(row, 10, totals.get('quantity', 0), number_format)
                worksheet.write(row, 11, '', text_format)
                worksheet.write(row, 12, '', text_format)
                worksheet.write(row, 13, totals.get('discount_amount', 0), currency_format)
                worksheet.write(row, 14, totals.get('net_prescription_value', 0), currency_format)
                row += 1
        
        # ========================================
        # ADD AREA MANAGER TOTALS
        # ========================================
        if area_manager_totals:
            row += 1
            worksheet.merge_range(row, 0, row, 14, 'AREA MANAGER TOTALS', total_format)
            row += 1
            
            for am_name, totals in area_manager_totals.items():
                worksheet.write(row, 0, '', text_format)
                worksheet.write(row, 1, '', text_format)
                worksheet.write(row, 2, '', text_format)
                worksheet.write(row, 3, '', text_format)
                worksheet.write(row, 4, '', text_format)
                worksheet.write(row, 5, am_name, area_manager_total_format)
                worksheet.write(row, 6, '', text_format)
                worksheet.write(row, 7, '', text_format)
                worksheet.write(row, 8, 'Total', area_manager_total_format)
                worksheet.write(row, 9, '', text_format)
                worksheet.write(row, 10, totals.get('quantity', 0), number_format)
                worksheet.write(row, 11, '', text_format)
                worksheet.write(row, 12, '', text_format)
                worksheet.write(row, 13, totals.get('discount_amount', 0), currency_format)
                worksheet.write(row, 14, totals.get('net_prescription_value', 0), currency_format)
                row += 1
        
        # ========================================
        # ADD GRAND TOTAL
        # ========================================
        row += 1
        worksheet.merge_range(row, 0, row, 14, 'GRAND TOTAL', total_format)
        row += 1
        
        worksheet.write(row, 0, '', text_format)
        worksheet.write(row, 1, '', text_format)
        worksheet.write(row, 2, '', text_format)
        worksheet.write(row, 3, '', text_format)
        worksheet.write(row, 4, '', text_format)
        worksheet.write(row, 5, '', text_format)
        worksheet.write(row, 6, '', text_format)
        worksheet.write(row, 7, '', text_format)
        worksheet.write(row, 8, 'Grand Total', total_format)
        worksheet.write(row, 9, '', text_format)
        worksheet.write(row, 10, grand_total.get('quantity', 0), number_format)
        worksheet.write(row, 11, '', text_format)
        worksheet.write(row, 12, '', text_format)
        worksheet.write(row, 13, grand_total.get('discount_amount', 0), currency_format)
        worksheet.write(row, 14, grand_total.get('net_prescription_value', 0), currency_format)

    def _generate_excel_report(self):
        """Generate Excel report with all sheets (YTD, MTD, WTD, Yesterday)"""
        
        # Get all date ranges
        date_ranges = self._get_date_ranges()
        
        # Prepare filters
        filters = {
            'area_manager_id': self.area_manager_id,
            'region': self.region,
            'clinic_ids': self.clinic_ids
        }
        
        # Create Excel file
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        
        # Process each date range
        sheets_created = 0
        for range_key, range_data in date_ranges.items():
            date_from = range_data['date_from']
            date_to = range_data['date_to']
            
            # Get appointments for this date range
            appointments = self._get_appointments_for_date_range(date_from, date_to, filters)
            
            if appointments:
                # Collect report data
                report_data = []
                processed_sale_orders = set()
                
                for appointment in appointments:
                    sale_order = appointment.sale_order_id
                    if not sale_order:
                        continue
                    
                    if sale_order.id in processed_sale_orders:
                        continue
                    
                    processed_sale_orders.add(sale_order.id)
                    
                    # Filter ONLY HA (Hearing Aid) products
                    # item_type = 'ha' on product template
                    sale_lines = sale_order.order_line.filtered(
                        lambda l: l.product_id 
                        and l.product_id.type in ['consu', 'service', 'combo']
                        and l.product_id.product_tmpl_id.item_type == 'ha'  # Only HA products
                    )
                    
                    if not sale_lines:
                        continue
                    
                    for line in sale_lines:
                        row_data = self._compute_prescription_metrics(appointment, sale_order, line)
                        if row_data:
                            report_data.append(row_data)
                
                if report_data:
                    # Create worksheet
                    sheet_name = range_key.upper()
                    worksheet = workbook.add_worksheet(sheet_name)
                    
                    # Write data to sheet
                    self._write_sheet_data(
                        workbook, 
                        worksheet, 
                        report_data, 
                        date_from, 
                        date_to, 
                        range_data['label']
                    )
                    sheets_created += 1
                    _logger.info("Created sheet %s with %s records", sheet_name, len(report_data))
        
        if sheets_created == 0:
            raise ValidationError(_('No HA (Hearing Aid) product prescriptions found for any date range.'))
        
        workbook.close()
        
        # ========================================
        # CREATE ATTACHMENT AND DOWNLOAD
        # ========================================
        file_data = output.getvalue()
        today = fields.Date.today()
        file_name = f"{self.file_name}_{today.strftime('%Y%m%d')}.xlsx"
        file_data_base64 = base64.b64encode(file_data)
        
        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'type': 'binary',
            'datas': file_data_base64,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': 'daily.prescription.report.wizard',
            'res_id': self.id
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new'
        }