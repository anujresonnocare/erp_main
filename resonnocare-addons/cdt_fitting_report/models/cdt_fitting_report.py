# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class CdtFittingReport(models.Model):
    _name = 'cdt.fitting.report'
    _description = 'CDT Fitting Report'
    _order = 'fitting_date desc, clinic_name'
    _rec_name = 'display_name'

    # ========================================
    # BASIC INFO FIELDS
    # ========================================
    clinic_id = fields.Many2one('resonnocare.clinic', string='Clinic', index=True)
    clinic_name = fields.Char(string='Clinic Name', related='clinic_id.name', store=True)
    clinic_code = fields.Char(string='Clinic Code', related='clinic_id.clinic_code', store=True)
    region = fields.Char(string='Region', related='clinic_id.region', store=True)
    area_manager_id = fields.Many2one('res.users', string='Area Manager', related='clinic_id.area_manager_id', store=True)
    area_manager_name = fields.Char(string='Area Manager', related='clinic_id.area_manager_id.name', store=True)
    clinic_type = fields.Selection([('h', 'H'), ('sis', 'SIS'), ('coco', 'COCO')], string='Clinic Type', related='clinic_id.clinic_type', store=True)
    cost_centre = fields.Char(string='Cost Centre', related='clinic_id.name', store=True)
    
    # ========================================
    # REPORT DATE RANGE FIELDS
    # ========================================
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    report_type = fields.Selection([
        ('ytd', 'Year to Date'), 
        ('mtd', 'Month to Date'), 
        ('wtd', 'Week to Date'), 
        ('yday', 'Yesterday'), 
        ('custom', 'Custom Range')
    ], string='Report Type', default='ytd')
    
    # ========================================
    # APPOINTMENT & FITTING DATA FIELDS
    # ========================================
    appointment_id = fields.Many2one('resonnocare.appointment', string='Appointment')
    fitting_date = fields.Date(string='Fitting Date')
    
    audiologist_id = fields.Many2one(
        'hr.employee',
        string='Audiologist',
        ondelete='set null',
        context={'active_test': False}
    )
    audiologist_name = fields.Char(
        string='Audiologist Name',
        related='audiologist_id.name',
        store=True,
        readonly=True
    )
    
    # ========================================
    # CLIENT INFORMATION
    # ========================================
    client_id = fields.Many2one('res.partner', string='Client')
    client_code = fields.Char(string='Client Code', related='client_id.ref', store=True)
    client_name = fields.Char(string='Name of Client', related='client_id.name', store=True)
    client_type = fields.Selection([
        ('new', 'New'),
        ('existing', 'Existing'),
        ('renew', 'Renew')
    ], string='Client Type', default='new')
    
    # ========================================
    # SALE ORDER INFORMATION
    # ========================================
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sale Order Line')
    product_id = fields.Many2one('product.product', string='Product')
    
    # ========================================
    # EQUIPMENT DETAILS
    # ========================================
    equipment_type = fields.Char(string='Type of Hearing Equipment & Accessories')
    quantity = fields.Integer(string='Quantity', default=1)
    unit_price = fields.Float(string='Unit Price (MRP)', digits=(16, 2))
    discount = fields.Float(string='Discount (%)', digits=(16, 2))
    discount_amount = fields.Float(string='Discount Amount (Rs.)', digits=(16, 2))
    subtotal = fields.Float(string='Subtotal (Rs.)', digits=(16, 2))
    gross = fields.Float(string='Gross (Rs.)', digits=(16, 2))
    total_amt_receivable = fields.Float(string='Total Amt. Receivable (Rs.)', digits=(16, 2))
    weekly_target = fields.Float(string='Weekly Target', digits=(16, 2))
    
    # ========================================
    # APPOINTMENT STATUS
    # ========================================
    status = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('checked_in', 'Checked In'),
        ('in_consultation', 'In Consultation'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show')
    ], string='Status', default='scheduled')
    
    # ========================================
    # SERIAL NUMBERS
    # ========================================
    serial_numbers = fields.Char(string='Serial Numbers')
    
    # ========================================
    # DISPLAY & FLAGS
    # ========================================
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    is_total_row = fields.Boolean(string='Is Total Row', default=False)
    is_area_manager_total = fields.Boolean(string='Is Area Manager Total', default=False)
    is_region_total = fields.Boolean(string='Is Region Total', default=False)
    active = fields.Boolean(string='Active', default=True)

    @api.depends('client_name', 'fitting_date', 'product_id')
    def _compute_display_name(self):
        for record in self:
            if record.is_region_total:
                record.display_name = f'{record.region} Total'
            elif record.is_area_manager_total:
                record.display_name = f'{record.area_manager_name} Total'
            else:
                record.display_name = f'{record.client_name or ""} - {record.fitting_date or ""}'

    def generate_report(self):
        self.ensure_one()
        date_from = self.date_from
        date_to = self.date_to
        report_type = self.report_type or 'ytd'
        if not date_from or not date_to:
            today = fields.Date.today()
            if report_type == 'ytd':
                date_from = date(today.year, 1, 1)
                date_to = today
            elif report_type == 'mtd':
                date_from = date(today.year, today.month, 1)
                date_to = today
            elif report_type == 'wtd':
                monday = today - relativedelta(days=today.weekday())
                date_from = monday
                date_to = today
            elif report_type == 'yday':
                yesterday = today - relativedelta(days=1)
                date_from = yesterday
                date_to = yesterday
        return self._generate_report_data(date_from, date_to, report_type)
    
    def _generate_report_data(self, date_from, date_to, report_type):
        _logger.info("=== _generate_report_data called ===")
        _logger.info("Date From: %s, Date To: %s, Report Type: %s", date_from, date_to, report_type)
        
        # Archive existing records instead of deleting
        existing = self.search([
            ('date_from', '=', date_from),
            ('date_to', '=', date_to),
            ('report_type', '=', report_type)
        ])
        existing.write({'active': False})
        
        # Get Fitting appointment type
        fitting_type = self.env['resonnocare.appointment.type'].search([('name', '=', 'Fitting')], limit=1)
        if not fitting_type:
            fitting_type = self.env['resonnocare.appointment.type'].search([('name', 'ilike', 'fitting')], limit=1)
        if not fitting_type:
            raise ValidationError(_('Fitting appointment type not found.'))
        
        fitting_appointments = self.env['resonnocare.appointment'].search([
            ('appointment_date', '>=', date_from),
            ('appointment_date', '<=', date_to),
            ('status', 'not in', ['cancelled', 'no_show']),
            ('appointment_type_id', '=', fitting_type.id)
        ])
        
        if not fitting_appointments:
            raise ValidationError(_('No fitting appointments found for the selected date range.'))
        
        report_records = []
        processed_sale_orders = set()
        
        for appointment in fitting_appointments:
            sale_order = appointment.sale_order_id
            if not sale_order:
                continue
            
            if sale_order.id in processed_sale_orders:
                continue
            
            processed_sale_orders.add(sale_order.id)
            
            # Get ONLY Hearing Aid (HA) products from the sale order
            # Filter by item_type == 'ha' on the product template
            sale_lines = sale_order.order_line.filtered(
                lambda l: l.product_id 
                and l.product_id.type in ['consu', 'service', 'combo']
                and l.product_id.product_tmpl_id.item_type == 'ha'  # Only Hearing Aids
            )
            
            if not sale_lines:
                continue
            
            # Get all serial numbers for this sale order
            serial_numbers = self._get_serial_numbers_from_sale_order(sale_order)
            _logger.info("Sale Order %s - Found %s serial numbers: %s", sale_order.id, len(serial_numbers), serial_numbers)
            
            if serial_numbers:
                # Create one record per serial number
                for serial_no in serial_numbers:
                    vals = self._compute_fitting_metrics(appointment, sale_order, serial_no, sale_lines)
                    if vals:
                        vals.update({
                            'date_from': date_from,
                            'date_to': date_to,
                            'report_type': report_type,
                            'is_total_row': False,
                            'is_area_manager_total': False,
                            'is_region_total': False,
                        })
                        report_records.append(vals)
            else:
                # No serial numbers, create one record with empty serial
                vals = self._compute_fitting_metrics(appointment, sale_order, '', sale_lines)
                if vals:
                    vals.update({
                        'date_from': date_from,
                        'date_to': date_to,
                        'report_type': report_type,
                        'is_total_row': False,
                        'is_area_manager_total': False,
                        'is_region_total': False,
                    })
                    report_records.append(vals)
        
        if not report_records:
            raise ValidationError(_('No fitting data with Hearing Aid products found for the selected date range.'))
        
        # Area Manager Totals
        area_managers = fitting_appointments.mapped('clinic_id.area_manager_id')
        for am in area_managers:
            if not am:
                continue
            am_appointments = fitting_appointments.filtered(lambda a: a.clinic_id.area_manager_id.id == am.id)
            if not am_appointments:
                continue
            am_vals = self._compute_aggregated_metrics(am_appointments)
            am_vals.update({
                'area_manager_id': am.id,
                'area_manager_name': am.name,
                'date_from': date_from,
                'date_to': date_to,
                'report_type': report_type,
                'is_total_row': True,
                'is_area_manager_total': True,
                'is_region_total': False,
                'clinic_id': False,
                'serial_numbers': '',  # No serial numbers for total rows
            })
            report_records.append(am_vals)
        
        # Region Totals
        regions = fitting_appointments.mapped('clinic_id.region')
        for region in regions:
            if not region:
                continue
            region_appointments = fitting_appointments.filtered(lambda a: a.clinic_id.region == region)
            if not region_appointments:
                continue
            region_vals = self._compute_aggregated_metrics(region_appointments)
            region_vals.update({
                'region': region,
                'date_from': date_from,
                'date_to': date_to,
                'report_type': report_type,
                'is_total_row': True,
                'is_area_manager_total': False,
                'is_region_total': True,
                'clinic_id': False,
                'area_manager_id': False,
                'area_manager_name': '',
                'serial_numbers': '',  # No serial numbers for total rows
            })
            report_records.append(region_vals)
        
        if report_records:
            self.create(report_records)
            _logger.info("Created %s report records", len(report_records))
        return {'type': 'ir.actions.client', 'tag': 'reload'}
    
    def _compute_fitting_metrics(self, appointment, sale_order, serial_no=None, sale_lines=None):
        """Compute fitting metrics for a sale order, only for Hearing Aid products"""
        vals = {}
        vals['clinic_id'] = appointment.clinic_id.id
        vals['clinic_name'] = appointment.clinic_id.name
        vals['region'] = appointment.clinic_id.region
        vals['area_manager_id'] = appointment.clinic_id.area_manager_id.id if appointment.clinic_id.area_manager_id else False
        vals['area_manager_name'] = appointment.clinic_id.area_manager_id.name if appointment.clinic_id.area_manager_id else ''
        vals['clinic_type'] = appointment.clinic_id.clinic_type
        vals['cost_centre'] = appointment.clinic_id.name
        vals['appointment_id'] = appointment.id
        vals['fitting_date'] = appointment.appointment_date
        vals['audiologist_id'] = appointment.audiologist_id.id if appointment.audiologist_id else False
        vals['audiologist_name'] = appointment.audiologist_id.name if appointment.audiologist_id else ''
        vals['client_id'] = appointment.patient_id.id
        vals['client_code'] = appointment.patient_id.patient_id if appointment.patient_id else ''
        vals['client_name'] = appointment.patient_id.name
        vals['client_type'] = self._get_client_type(appointment)
        vals['sale_order_id'] = sale_order.id
        
        # If sale_lines not provided, get only HA products
        if sale_lines is None:
            sale_lines = sale_order.order_line.filtered(
                lambda l: l.product_id 
                and l.product_id.type in ['consu', 'service', 'combo']
                and l.product_id.product_tmpl_id.item_type == 'ha'
            )
        
        # Aggregate all HA products into a single string
        product_names = []
        total_quantity = 0
        total_unit_price = 0
        total_discount = 0
        total_discount_amount = 0
        total_subtotal = 0
        total_gross = 0
        total_receivable = 0
        
        for line in sale_lines:
            product_names.append(line.product_id.name or 'Hearing Aid')
            qty = int(line.product_uom_qty) if line.product_uom_qty else 1
            total_quantity += qty
            
            unit_price = line.price_unit or line.product_id.lst_price or 0.0
            total_unit_price += unit_price * qty
            
            discount_percentage = line.discount or 0.0
            subtotal = unit_price * qty
            discount_amount = subtotal * (discount_percentage / 100)
            
            total_discount += discount_percentage
            total_discount_amount += discount_amount
            total_subtotal += subtotal - discount_amount
            total_gross += subtotal
            total_receivable += subtotal - discount_amount
        
        # Set the aggregated values
        vals['equipment_type'] = ', '.join(product_names) if product_names else 'Hearing Aid'
        vals['quantity'] = total_quantity
        vals['unit_price'] = total_unit_price / max(len(sale_lines), 1)  # Average unit price
        vals['discount'] = total_discount / max(len(sale_lines), 1)  # Average discount
        vals['discount_amount'] = total_discount_amount
        vals['subtotal'] = total_subtotal
        vals['gross'] = total_gross
        vals['total_amt_receivable'] = total_receivable
        vals['weekly_target'] = self._get_weekly_target(appointment.clinic_id)
        vals['status'] = appointment.status
        
        # If a specific serial number is provided, use it; otherwise keep as empty
        vals['serial_numbers'] = serial_no or ''
        
        # Store first sale order line ID for reference
        vals['sale_order_line_id'] = sale_lines[0].id if sale_lines else False
        vals['product_id'] = sale_lines[0].product_id.id if sale_lines else False
        
        return vals

    def _get_serial_numbers_from_sale_order(self, sale_order):
        """Get all serial numbers from stock moves linked to a sale order"""
        serial_numbers = []
        
        if not sale_order:
            return serial_numbers
        
        # Get all sale order lines
        for sale_line in sale_order.order_line:
            # Get stock moves from each sale order line's move_ids
            for move in sale_line.move_ids:
                # Check if the move is done or assigned (has serial numbers)
                if move.state in ['done', 'assigned']:
                    for move_line in move.move_line_ids:
                        if move_line.lot_id and move_line.lot_id.name:
                            serial_numbers.append(move_line.lot_id.name)
        
        # Remove duplicates while preserving order
        serial_numbers = list(dict.fromkeys(serial_numbers))
        
        return serial_numbers
    
    def _get_client_type(self, appointment):
        if not appointment.patient_id:
            return 'new'
        previous = self.env['resonnocare.appointment'].search([
            ('patient_id', '=', appointment.patient_id.id),
            ('appointment_date', '<', appointment.appointment_date),
            ('status', 'not in', ['cancelled', 'no_show'])
        ], limit=1)
        if previous:
            last = self.env['resonnocare.appointment'].search([
                ('patient_id', '=', appointment.patient_id.id),
                ('appointment_date', '<', appointment.appointment_date),
                ('status', 'not in', ['cancelled', 'no_show'])
            ], order='appointment_date desc', limit=1)
            if last and (appointment.appointment_date - last.appointment_date).days > 365:
                return 'renew'
            return 'existing'
        return 'new'
    
    def _get_weekly_target(self, clinic):
        if clinic.clinic_type == 'sis':
            return 50000.0
        elif clinic.clinic_type == 'coco':
            return 30000.0
        return 20000.0
    
    def _compute_aggregated_metrics(self, appointments):
        """Compute aggregated metrics for a group of appointments"""
        aggregated = {}
        numeric_fields = [
            'quantity', 'unit_price', 'discount_amount', 'subtotal',
            'gross', 'total_amt_receivable', 'weekly_target'
        ]
        
        # Track processed sale orders to avoid double counting
        processed_sale_orders = set()
        
        for appointment in appointments:
            sale_order = appointment.sale_order_id
            if not sale_order:
                continue
            
            # Skip if this sale order was already processed
            if sale_order.id in processed_sale_orders:
                continue
            processed_sale_orders.add(sale_order.id)
            
            # Get only HA products
            sale_lines = sale_order.order_line.filtered(
                lambda l: l.product_id 
                and l.product_id.type in ['consu', 'service', 'combo']
                and l.product_id.product_tmpl_id.item_type == 'ha'
            )
            
            if not sale_lines:
                continue
            
            # Get base metrics for the sale order (without serial number)
            vals = self._compute_fitting_metrics(appointment, sale_order, '', sale_lines)
            
            # Sum numeric fields
            for key, value in vals.items():
                if key in numeric_fields and value is not None:
                    aggregated[key] = aggregated.get(key, 0) + value
            
            # For equipment_type, collect all product names
            if 'equipment_type' in vals and vals['equipment_type']:
                if 'equipment_type' not in aggregated:
                    aggregated['equipment_type'] = []
                aggregated['equipment_type'].append(vals['equipment_type'])
        
        # Convert equipment_type list to string
        if 'equipment_type' in aggregated and isinstance(aggregated['equipment_type'], list):
            # Get unique product names
            unique_products = set()
            for eq_type in aggregated['equipment_type']:
                for product in eq_type.split(', '):
                    unique_products.add(product)
            aggregated['equipment_type'] = ', '.join(sorted(unique_products))
        
        aggregated['client_name'] = 'Total'
        return aggregated
    
    def action_view_appointment(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Appointment',
            'res_model': 'resonnocare.appointment',
            'view_mode': 'form',
            'res_id': self.appointment_id.id,
            'target': 'current'
        }
    
    def action_archive(self):
        """Archive selected records"""
        self.write({'active': False})
    
    def action_unarchive(self):
        """Unarchive selected records"""
        self.write({'active': True})