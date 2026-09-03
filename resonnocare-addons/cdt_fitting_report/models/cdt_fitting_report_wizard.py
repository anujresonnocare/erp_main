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
        
        if not self.date_from or not self.date_to:
            raise ValidationError(_('Please select valid date range.'))
        
        if self.date_from > self.date_to:
            raise ValidationError(_('Date From cannot be greater than Date To.'))
        
        if self.report_format in ['excel', 'both']:
            return self._generate_excel_report()
        elif self.report_format == 'pdf':
            return self._generate_pdf_report()
        
        return False

    def _get_fitting_appointment_data(self):
        """Fetch completed fitting appointments with their related data"""
        fitting_type = self.env['resonnocare.appointment.type'].search([
            ('name', 'ilike', 'fitting')
        ], limit=1)

        if not fitting_type:
            raise ValidationError(_('Fitting appointment type not found. Please configure it in Masters.'))

        # Build domain for appointments - only completed
        domain = [
            ('appointment_type_id', '=', fitting_type.id),
            ('status', '=', 'completed'),
            ('appointment_date', '>=', self.date_from),
            ('appointment_date', '<=', self.date_to)
        ]
        
        # Apply filters
        if self.area_manager_id:
            domain.append(('clinic_id.area_manager_id', '=', self.area_manager_id.id))
        if self.region:
            domain.append(('clinic_id.region', '=', self.region))
        if self.clinic_ids:
            domain.append(('clinic_id', 'in', self.clinic_ids.ids))

        appointments = self.env['resonnocare.appointment'].search(domain)
        
        if not appointments:
            raise ValidationError(_('No completed fitting appointments found for the selected criteria.'))

        return appointments

    def _calculate_discount(self, line):
        """Calculate discount percentage and amount from sale order line"""
        discount_percent = 0.0
        discount_amount = 0.0
        
        list_price = line.product_id.lst_price or line.price_unit
        unit_price = line.price_unit
        quantity = line.product_uom_qty
        gross_mrp = quantity * list_price
        
        # Check if line has discount_type field
        if hasattr(line, 'discount_type'):
            if line.discount_type == 'percent':
                # Percentage discount
                discount_percent = line.discount or 0.0
                discount_amount = (gross_mrp * discount_percent) / 100
            elif line.discount_type == 'fixed':
                # Fixed amount discount per unit
                discount_fixed = line.discount_fixed or 0.0
                discount_amount = discount_fixed * quantity
                discount_percent = (discount_amount / gross_mrp * 100) if gross_mrp > 0 else 0.0
        else:
            # Fallback: calculate from price difference
            if list_price > 0 and unit_price < list_price:
                discount_percent = ((list_price - unit_price) / list_price) * 100
                discount_amount = gross_mrp - (quantity * unit_price)
        
        return discount_percent, discount_amount

    def _get_invoice_details(self, sale_order):
        """Get invoice name and date from sale order"""
        invoice_name = ''
        invoice_date = ''
        
        if sale_order:
            # Get all invoices related to this sale order
            invoices = sale_order.invoice_ids.filtered(
                lambda inv: inv.move_type == 'out_invoice' and inv.state != 'cancel'
            )
            
            if invoices:
                # Get the first posted invoice or the latest one
                posted_invoices = invoices.filtered(lambda inv: inv.state == 'posted')
                if posted_invoices:
                    invoice = posted_invoices[0]
                else:
                    invoice = invoices[0]
                
                invoice_name = invoice.name or ''
                invoice_date = invoice.invoice_date or invoice.date or ''
        
        return invoice_name, invoice_date

    def _generate_excel_report(self):
        appointments = self._get_fitting_appointment_data()
        
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        
        # Define formats
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
        
        # Red format for cancelled order column
        red_format = workbook.add_format({
            'border': 1, 
            'font_size': 10, 
            'fg_color': '#FF0000',
            'bold': True,
            'align': 'center',
            'valign': 'vcenter'
        })

        # Status color formats
        status_colors = {
            'draft': '#FFE4E1',
            'scheduled': '#E0FFFF',
            'checked_in': '#FFFACD',
            'in_consultation': '#FFDAB9',
            'completed': '#98FB98',
            'cancelled': '#FFC0C0',
            'no_show': '#D3D3D3'
        }
        
        status_map = {
            'draft': 'Draft',
            'scheduled': 'Scheduled',
            'checked_in': 'Checked In',
            'in_consultation': 'In Consultation',
            'completed': 'Completed',
            'cancelled': 'Cancelled',
            'no_show': 'No Show'
        }

        # Clinic type mapping
        clinic_type_map = {
            'h': 'H',
            'sis': 'SIS',
            'coco': 'COCO'
        }

        sheet_name = self.report_type.upper()
        worksheet = workbook.add_worksheet(sheet_name)
        
        # Title
        title_text = f'Fitting Report: {self.date_from.strftime("%d %b %Y")} To {self.date_to.strftime("%d %b %Y")}'
        if self.area_manager_id:
            title_text += f' - AM: {self.area_manager_id.name}'
        if self.region:
            title_text += f' - Region: {self.region}'
        worksheet.merge_range('A1:V1', title_text, title_format)
        
        # Headers - updated with new columns
        headers = [
            'Fitting Date',
            'Audiologist Name',
            'Patient Code',
            'Name of Patient',
            'Patient Type',
            'Description Of Item',
            'Quantity',
            'MRP (Unit Price)',
            'Gross MRP (Rs.)',
            'Discount (%)',
            'Discount Amount (Rs.)',
            'Net Sale (Rs.)',
            'Invoice Name',
            'Invoice Date',
            'Cancelled Order',
            'Clinic Name',
            'Cost Centre',
            'Weekly Target (Rs.)',
            'Region',
            'ABM',
            'Type of Clinic',
            'Status'
        ]
        
        # Set column widths - updated with new columns
        col_widths = [14, 20, 14, 25, 14, 35, 10, 16, 16, 12, 18, 22, 20, 14, 16, 45, 45, 18, 14, 18, 14, 14]
        
        for col, (header, width) in enumerate(zip(headers, col_widths)):
            worksheet.write(1, col, header, header_format)
            worksheet.set_column(col, col, width)
        
        row = 2
        
        # Process each appointment
        for appointment in appointments:
            # Get sale order (check both direct and parent)
            sale_order = appointment.sale_order_id or appointment.parent_appointment_id.sale_order_id
            
            if not sale_order:
                continue

            # Get invoice details
            invoice_name, invoice_date = self._get_invoice_details(sale_order)

            # Get serial numbers from completed deliveries
            serial_numbers = []
            for picking in sale_order.picking_ids.filtered(lambda p: p.state == 'done'):
                for move_line in picking.move_line_ids:
                    if move_line.lot_id:
                        serial_numbers.append(move_line.lot_id.name)
                    elif move_line.lot_name:
                        serial_numbers.append(move_line.lot_name)
            
            serial_numbers_str = ', '.join(set(serial_numbers)) if serial_numbers else ''

            # Process each sale order line - ONLY HA products
            for line in sale_order.order_line:
                if not line.product_id:
                    continue
                
                # Check if product has item_type field and it's 'ha'
                product_item_type = False
                if hasattr(line.product_id, 'item_type'):
                    product_item_type = line.product_id.item_type
                elif hasattr(line.product_id.product_tmpl_id, 'item_type'):
                    product_item_type = line.product_id.product_tmpl_id.item_type
                
                # Skip if item_type is not 'ha'
                if product_item_type != 'ha':
                    continue

                # Calculate values
                list_price = line.product_id.lst_price or line.price_unit
                unit_price = line.price_unit
                quantity = line.product_uom_qty
                
                gross_mrp = quantity * list_price
                
                # Use price_subtotal from the line (already includes discount)
                total_sale = line.price_subtotal if hasattr(line, 'price_subtotal') else (quantity * unit_price)
                
                # Calculate discount using the helper method
                discount_percent, discount_amount = self._calculate_discount(line)

                # Determine patient type
                patient_type = 'Existing'
                if appointment.patient_id:
                    if appointment.patient_id.create_date and appointment.patient_id.create_date.date() == appointment.appointment_date:
                        patient_type = 'New'
                    elif appointment.patient_id.referral_source == 'walkin':
                        patient_type = 'Walk-in'
                    elif appointment.patient_id.referral_source == 'crm':
                        patient_type = 'CRM'
                    else:
                        patient_type = 'Existing'

                # Get clinic data from the clinic model
                clinic = appointment.clinic_id
                clinic_type_display = clinic_type_map.get(clinic.clinic_type, '') if clinic else ''
                clinic_name = clinic.name if clinic else ''
                # Cost Centre - using clinic name only
                cost_centre = clinic_name
                weekly_target = clinic.weekly_target if hasattr(clinic, 'weekly_target') and clinic.weekly_target else 0.0
                region = clinic.region if clinic else ''
                area_manager = clinic.area_manager_id.name if clinic and clinic.area_manager_id else ''

                # Write row data with new columns
                row_data = [
                    appointment.appointment_date,  # Fitting Date
                    appointment.audiologist_id.name if appointment.audiologist_id else '',  # Audiologist Name
                    appointment.patient_id.patient_id or appointment.patient_id.id or '',  # Patient Code
                    appointment.patient_id.name if appointment.patient_id else '',  # Name of Patient
                    patient_type,  # Patient Type
                    line.product_id.name,  # Description Of Item
                    quantity,  # Quantity
                    unit_price,  # MRP (Unit Price)
                    gross_mrp,  # Gross MRP (Rs.)
                    discount_percent,  # Discount (%)
                    discount_amount,  # Discount Amount (Rs.)
                    total_sale,  # Gross Sale (Rs.)
                    invoice_name,  # Invoice Name
                    invoice_date,  # Invoice Date
                    '',  # Cancelled Order - always blank
                    clinic_name,  # Clinic Name
                    cost_centre,  # Cost Centre (same as Clinic Name)
                    weekly_target,  # Weekly Target (Rs.)
                    region,  # Region
                    area_manager,  # ABM
                    clinic_type_display,  # Type of Clinic
                    status_map.get(appointment.status, appointment.status),  # Status
                ]

                # Write each cell with appropriate formatting
                col = 0
                for idx, value in enumerate(row_data):
                    if idx == 0:  # Date
                        worksheet.write(row, col, value, date_format)
                    elif idx == 14:  # Cancelled Order - always blank and in red
                        worksheet.write(row, col, 'CANCELLED', red_format)
                    elif idx in [6]:  # Quantity
                        worksheet.write(row, col, value or 0, number_format)
                    elif idx in [7, 8, 10, 11, 17]:  # Monetary values
                        worksheet.write(row, col, value or 0, currency_format)
                    elif idx == 9:  # Discount percentage
                        worksheet.write(row, col, (value / 100) if value else 0, percent_format)
                    elif idx == 13:  # Invoice Date
                        worksheet.write(row, col, value, date_format)
                    elif idx == 21:  # Status - with color
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

        workbook.close()
        
        file_data = output.getvalue()
        file_name = f"{self.file_name}_{self.report_type}_{self.date_from.strftime('%Y%m%d')}_{self.date_to.strftime('%Y%m%d')}.xlsx"
        file_data_base64 = base64.b64encode(file_data)
        
        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'type': 'binary',
            'datas': file_data_base64,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': 'cdt.fitting.report.wizard',
            'res_id': self.id
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new'
        }

    def _generate_pdf_report(self):
        """Placeholder for PDF report generation"""
        raise ValidationError(_('PDF report generation is not yet implemented. Please use Excel format.'))