# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date, datetime, timedelta
import io
import base64
import xlsxwriter
import logging
from collections import OrderedDict

_logger = logging.getLogger(__name__)


class DailyPrescriptionReportWizard(models.TransientModel):
    _name = 'daily.prescription.report.wizard'
    _description = 'Daily Prescription Report Wizard'

    # ========================================
    # WIZARD FIELDS
    # ========================================
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
    file_name = fields.Char(string='File Name', default='Daily_Prescription_Report')

    @api.onchange('report_type')
    def _onchange_report_type(self):
        today = fields.Date.today()
        if self.report_type == 'ytd':
            if today.month >= 4:
                self.date_from = date(today.year, 4, 1)
            else:
                self.date_from = date(today.year - 1, 4, 1)
            self.date_to = today
        elif self.report_type == 'mtd':
            self.date_from = date(today.year, today.month, 1)
            self.date_to = today
        elif self.report_type == 'wtd':
            monday = today - timedelta(days=today.weekday())
            self.date_from = monday
            self.date_to = today
        elif self.report_type == 'yday':
            yesterday = today - timedelta(days=1)
            self.date_from = yesterday
            self.date_to = yesterday
        else:
            self.date_from = False
            self.date_to = False

    def print_report(self):
        """Generate and download the Excel report"""
        self.ensure_one()

        if not self.date_from or not self.date_to:
            raise ValidationError(_('Please select valid date range.'))

        if self.date_from > self.date_to:
            raise ValidationError(_('Date From cannot be greater than Date To.'))

        return self._generate_excel_report()

    def _get_appointments(self):
        """Fetch device appointments only (sale_type = 'device')"""
        device_appointment_types = self.env['resonnocare.appointment.type'].search([
            ('sale_type', '=', 'device')
        ])

        if not device_appointment_types:
            raise ValidationError(_('No device appointment types found. Please configure appointment types with sale_type = Device.'))

        domain = [
            ('appointment_date', '>=', self.date_from),
            ('appointment_date', '<=', self.date_to),
            ('status', 'not in', ['cancelled', 'no_show']),
            ('appointment_type_id', 'in', device_appointment_types.ids)
        ]

        if self.area_manager_id:
            domain.append(('clinic_id.area_manager_id', '=', self.area_manager_id.id))
        if self.region:
            domain.append(('clinic_id.region', '=', self.region))
        if self.clinic_ids:
            domain.append(('clinic_id', 'in', self.clinic_ids.ids))

        appointments = self.env['resonnocare.appointment'].search(domain)
        _logger.info("Found %s device appointments (excluding cancelled and no-show)", len(appointments))
        return appointments

    def _calculate_discount(self, line):
        """Calculate discount percentage and amount"""
        discount_percent = 0.0
        discount_amount = 0.0

        list_price = line.product_id.lst_price or line.price_unit
        quantity = line.product_uom_qty
        gross_mrp = quantity * list_price

        if hasattr(line, 'discount_type'):
            if line.discount_type == 'percent':
                discount_percent = line.discount or 0.0
                discount_amount = (gross_mrp * discount_percent) / 100
            elif line.discount_type == 'fixed':
                discount_fixed = line.discount_fixed or 0.0
                discount_amount = discount_fixed * quantity
                discount_percent = (discount_amount / gross_mrp * 100) if gross_mrp > 0 else 0.0
        else:
            if list_price > 0 and line.price_unit < list_price:
                discount_percent = ((list_price - line.price_unit) / list_price) * 100
                discount_amount = gross_mrp - (quantity * line.price_unit)

        return discount_percent, discount_amount

    def _get_item_style(self, product):
        """Get item style from product template"""
        if not product:
            return ''

        if hasattr(product, 'item_style'):
            return product.item_style or ''
        elif hasattr(product.product_tmpl_id, 'item_style'):
            return product.product_tmpl_id.item_style or ''

        return ''

    def _get_advance_received(self, sale_order, appointment):
        """
        Advance Received = Sale Order Total - Balance Due
        (Balance Due comes from the appointment)
        """
        if not sale_order:
            return 0.0

        sale_total = sale_order.amount_total or 0.0
        balance_due = 0.0

        if appointment and hasattr(appointment, 'balance_due'):
            balance_due = appointment.balance_due or 0.0

        advance = sale_total - balance_due
        return advance if advance > 0 else 0.0

    def _get_patient_source(self, patient):
        """Get patient source from ref_source (Many2one)"""
        if not patient:
            return ''
        if hasattr(patient, 'ref_source') and patient.ref_source:
            return patient.ref_source.name or ''
        return ''

    def _generate_excel_report(self):
        """Generate Excel report with prescription data"""
        appointments = self._get_appointments()

        if not appointments:
            raise ValidationError(_('No device appointments found for the selected criteria.'))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)

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
        percent_format = workbook.add_format({
            'num_format': '0.00%',
            'border': 1,
            'font_size': 10
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
        am_total_format = workbook.add_format({
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

        status_colors = {
            'draft': '#FFE4E1',
            'scheduled': '#E0FFFF',
            'checked_in': '#FFFACD',
            'in_consultation': '#FFDAB9',
            'completed': '#98FB98',
        }
        status_map = {
            'draft': 'Draft',
            'scheduled': 'Scheduled',
            'checked_in': 'Checked In',
            'in_consultation': 'In Consultation',
            'completed': 'Completed',
        }

        clinic_type_map = {
            'h': 'H',
            'sis': 'SIS',
            'coco': 'COCO'
        }
        clinic_subtype_map = {
            'b2b': 'B2B',
            'b2c': 'B2C'
        }

        # ========================================
        # CREATE WORKSHEET
        # ========================================
        sheet_name = self.report_type.upper()
        worksheet = workbook.add_worksheet(sheet_name)

        report_label = {
            'ytd': 'Year to Date',
            'mtd': 'Month to Date',
            'wtd': 'Week to Date',
            'yday': 'Yesterday',
            'custom': 'Custom Range'
        }.get(self.report_type, 'Custom Range')

        title_text = f'Daily Prescription Report - {report_label}: {self.date_from.strftime("%d %b %Y")} To {self.date_to.strftime("%d %b %Y")}'
        if self.area_manager_id:
            title_text += f' - AM: {self.area_manager_id.name}'
        if self.region:
            title_text += f' - Region: {self.region}'
        worksheet.merge_range('A1:T1', title_text, title_format)

        # ========================================
        # HEADERS
        # ========================================
        headers = [
            'Date',
            'Clinic Name',
            'Region',
            'ABM',
            'Type of Clinic',
            'Clinic Sub Type',
            'Audiologist Name',
            'Patient Code',
            'Name of Patient',
            'Patient Source',
            'Description Of Item (Left Ear)',
            'Description Of Item (Right Ear)',
            'Item Style',
            'Quantity',
            'Gross MRP (Unit Price)',
            'Discount (%)',
            'Discount Amount (Rs.)',
            'Advance Received',
            'Net Sale (Rs.)',
            'Status'
        ]

        col_widths = [12, 30, 12, 18, 12, 12, 20, 12, 22, 16, 30, 30, 18, 10, 16, 10, 16, 16, 16, 12]

        for col, (header, width) in enumerate(zip(headers, col_widths)):
            worksheet.write(1, col, header, header_format)
            worksheet.set_column(col, col, width)

        row = 2
        all_report_data = []

        # ========================================
        # PROCESS APPOINTMENTS
        # ========================================
        for appointment in appointments:
            sale_order = appointment.sale_order_id or appointment.parent_appointment_id.sale_order_id
            if not sale_order:
                continue

            # ------------------------------------------------
            # Collect HA lines from sale order
            # ------------------------------------------------
            ha_lines = []
            for line in sale_order.order_line:
                if not line.product_id:
                    continue

                product_item_type = False
                if hasattr(line.product_id, 'item_type'):
                    product_item_type = line.product_id.item_type
                elif hasattr(line.product_id.product_tmpl_id, 'item_type'):
                    product_item_type = line.product_id.product_tmpl_id.item_type

                if product_item_type != 'ha':
                    continue

                ha_lines.append(line)

            if not ha_lines:
                continue

            # ------------------------------------------------
            # GROUP LINES BY PRODUCT NAME
            # Same name -> pair one Left + one Right, quantity = 2
            # Single leftover -> Left only, quantity = 1
            # ------------------------------------------------
            product_groups = OrderedDict()
            for line in ha_lines:
                pname = line.product_id.name
                product_groups.setdefault(pname, []).append(line)

            paired_rows = []
            for pname, lines in product_groups.items():
                lines = sorted(lines, key=lambda l: l.id)
                idx = 0
                while idx < len(lines):
                    if idx + 1 < len(lines):
                        left_line = lines[idx]
                        right_line = lines[idx + 1]
                        paired_rows.append({
                            'left_line': left_line,
                            'right_line': right_line,
                            'left_name': left_line.product_id.name,
                            'right_name': right_line.product_id.name,
                            'quantity': 2,
                            'lines': [left_line, right_line],
                        })
                        idx += 2
                    else:
                        single_line = lines[idx]
                        paired_rows.append({
                            'left_line': single_line,
                            'right_line': None,
                            'left_name': single_line.product_id.name,
                            'right_name': '',
                            'quantity': 1,
                            'lines': [single_line],
                        })
                        idx += 1

            # ------------------------------------------------
            # Advance Received = Sale Order Total - Balance Due
            # ------------------------------------------------
            advance_received = self._get_advance_received(sale_order, appointment)

            # ------------------------------------------------
            # Patient Source from ref_source (Many2one)
            # ------------------------------------------------
            patient_source = self._get_patient_source(appointment.patient_id)

            # Clinic info
            clinic = appointment.clinic_id
            clinic_type_display = clinic_type_map.get(clinic.clinic_type, '') if clinic else ''
            clinic_subtype_display = clinic_subtype_map.get(clinic.clinic_subtype, '') if clinic else ''
            clinic_name = clinic.name if clinic else ''
            region = clinic.region if clinic else ''
            area_manager = clinic.area_manager_id.name if clinic and clinic.area_manager_id else ''

            # ------------------------------------------------
            # WRITE ONE ROW PER PAIRED GROUP
            # ------------------------------------------------
            for pair in paired_rows:
                left_line = pair['left_line']
                right_line = pair['right_line']
                quantity = pair['quantity']

                ref_line = left_line or right_line
                item_style = self._get_item_style(ref_line.product_id) if ref_line else ''

                unit_price = left_line.price_unit if left_line else (right_line.price_unit if right_line else 0.0)

                total_discount_amount = 0.0
                total_discount_percent = 0.0
                total_net_sale = 0.0

                for l in pair['lines']:
                    dp, da = self._calculate_discount(l)
                    total_discount_amount += da
                    total_net_sale += (l.price_subtotal if hasattr(l, 'price_subtotal') else l.product_uom_qty * l.price_unit)

                gross_for_pct = sum(
                    (l.product_uom_qty * (l.product_id.lst_price or l.price_unit))
                    for l in pair['lines']
                )
                if gross_for_pct > 0:
                    total_discount_percent = (total_discount_amount / gross_for_pct) * 100

                if quantity == 1 and len(pair['lines']) == 1:
                    l = pair['lines'][0]
                    dp, da = self._calculate_discount(l)
                    total_discount_percent = dp
                    total_discount_amount = da

                row_data = {
                    'date': appointment.appointment_date,
                    'clinic_name': clinic_name,
                    'region': region,
                    'area_manager': area_manager,
                    'clinic_type': clinic_type_display,
                    'clinic_subtype': clinic_subtype_display,
                    'audiologist': appointment.audiologist_id.name if appointment.audiologist_id else '',
                    'patient_code': appointment.patient_id.patient_id or appointment.patient_id.id or '',
                    'patient_name': appointment.patient_id.name if appointment.patient_id else '',
                    'patient_source': patient_source,
                    'left_ear_item': pair['left_name'],
                    'right_ear_item': pair['right_name'],
                    'item_style': item_style,
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'discount_percent': total_discount_percent,
                    'discount_amount': total_discount_amount,
                    'advance_received': advance_received,
                    'total_sale': total_net_sale,
                    'status': status_map.get(appointment.status, appointment.status)
                }
                all_report_data.append(row_data)

                col = 0
                for idx, value in enumerate([
                    row_data['date'],
                    row_data['clinic_name'],
                    row_data['region'],
                    row_data['area_manager'],
                    row_data['clinic_type'],
                    row_data['clinic_subtype'],
                    row_data['audiologist'],
                    row_data['patient_code'],
                    row_data['patient_name'],
                    row_data['patient_source'],
                    row_data['left_ear_item'],
                    row_data['right_ear_item'],
                    row_data['item_style'],
                    row_data['quantity'],
                    row_data['unit_price'],
                    row_data['discount_percent'],
                    row_data['discount_amount'],
                    row_data['advance_received'],
                    row_data['total_sale'],
                    row_data['status']
                ]):
                    if idx == 0:
                        worksheet.write(row, col, value, date_format)
                    elif idx == 13:
                        worksheet.write(row, col, value or 0, number_format)
                    elif idx in [14, 16, 17, 18]:
                        worksheet.write(row, col, value or 0, currency_format)
                    elif idx == 15:
                        worksheet.write(row, col, (value / 100) if value else 0, percent_format)
                    elif idx == 19:
                        status_color = status_colors.get(appointment.status, '')
                        if status_color:
                            status_format = workbook.add_format({
                                'border': 1,
                                'font_size': 10,
                                'fg_color': status_color
                            })
                            worksheet.write(row, col, value, status_format)
                        else:
                            worksheet.write(row, col, value, text_format)
                    else:
                        worksheet.write(row, col, value or '', text_format)
                    col += 1
                row += 1

        # ========================================
        # CALCULATE AND ADD TOTALS
        # ========================================
        if all_report_data:
            am_totals = {}
            for data in all_report_data:
                am = data.get('area_manager', '')
                if am:
                    if am not in am_totals:
                        am_totals[am] = {'quantity': 0, 'discount_amount': 0, 'advance_received': 0, 'total_sale': 0}
                    am_totals[am]['quantity'] += data.get('quantity', 0)
                    am_totals[am]['discount_amount'] += data.get('discount_amount', 0)
                    am_totals[am]['advance_received'] += data.get('advance_received', 0)
                    am_totals[am]['total_sale'] += data.get('total_sale', 0)

            region_totals = {}
            for data in all_report_data:
                region = data.get('region', '')
                if region:
                    if region not in region_totals:
                        region_totals[region] = {'quantity': 0, 'discount_amount': 0, 'advance_received': 0, 'total_sale': 0}
                    region_totals[region]['quantity'] += data.get('quantity', 0)
                    region_totals[region]['discount_amount'] += data.get('discount_amount', 0)
                    region_totals[region]['advance_received'] += data.get('advance_received', 0)
                    region_totals[region]['total_sale'] += data.get('total_sale', 0)

            grand_total = {
                'quantity': sum(d.get('quantity', 0) for d in all_report_data),
                'discount_amount': sum(d.get('discount_amount', 0) for d in all_report_data),
                'advance_received': sum(d.get('advance_received', 0) for d in all_report_data),
                'total_sale': sum(d.get('total_sale', 0) for d in all_report_data)
            }

            # Region Totals
            if region_totals:
                row += 1
                worksheet.merge_range(row, 0, row, 19, 'REGION TOTALS', total_format)
                row += 1
                for region, totals in region_totals.items():
                    worksheet.write(row, 1, region, region_total_format)
                    worksheet.write(row, 13, totals.get('quantity', 0), number_format)
                    worksheet.write(row, 16, totals.get('discount_amount', 0), currency_format)
                    worksheet.write(row, 17, totals.get('advance_received', 0), currency_format)
                    worksheet.write(row, 18, totals.get('total_sale', 0), currency_format)
                    row += 1

            # Area Manager Totals
            if am_totals:
                row += 1
                worksheet.merge_range(row, 0, row, 19, 'AREA MANAGER TOTALS', total_format)
                row += 1
                for am, totals in am_totals.items():
                    worksheet.write(row, 3, am, am_total_format)
                    worksheet.write(row, 13, totals.get('quantity', 0), number_format)
                    worksheet.write(row, 16, totals.get('discount_amount', 0), currency_format)
                    worksheet.write(row, 17, totals.get('advance_received', 0), currency_format)
                    worksheet.write(row, 18, totals.get('total_sale', 0), currency_format)
                    row += 1

            # Grand Total
            row += 1
            worksheet.merge_range(row, 0, row, 19, 'GRAND TOTAL', total_format)
            row += 1
            worksheet.write(row, 13, grand_total.get('quantity', 0), number_format)
            worksheet.write(row, 16, grand_total.get('discount_amount', 0), currency_format)
            worksheet.write(row, 17, grand_total.get('advance_received', 0), currency_format)
            worksheet.write(row, 18, grand_total.get('total_sale', 0), currency_format)

        workbook.close()

        file_data = output.getvalue()
        today = fields.Date.today()
        file_name = f"{self.file_name}_{self.report_type}_{today.strftime('%Y%m%d')}.xlsx"
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