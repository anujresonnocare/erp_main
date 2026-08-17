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
    serial_numbers = fields.Char(string='Serial Numbers', compute='_compute_serial_numbers', store=True)
    
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

    @api.depends('sale_order_id')
    def _compute_serial_numbers(self):
        """Compute serial numbers from the delivery (stock move)"""
        for record in self:
            serial_numbers = []
            if record.sale_order_id:
                # Find the delivery/picking for this sale order
                pickings = self.env['stock.picking'].search([
                    ('origin', '=', record.sale_order_id.name),
                    ('state', 'in', ['assigned', 'done'])
                ], limit=1)
                
                if pickings:
                    # Get all move lines with serial numbers
                    for move_line in pickings.move_line_ids:
                        if move_line.lot_id and move_line.lot_id.name:
                            serial_numbers.append(move_line.lot_id.name)
            
            record.serial_numbers = ', '.join(serial_numbers) if serial_numbers else ''

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
        
        # ========================================
        # TRACK PROCESSED SALE ORDERS TO AVOID DUPLICATES
        # ========================================
        processed_sale_orders = set()
        
        for appointment in fitting_appointments:
            print(f"Processing Appointment ID: {appointment.id}, Date: {appointment.appointment_date}, Clinic: {appointment.clinic_id.name}")
            
            sale_order = appointment.sale_order_id
            print(f"Linked Sale Order: {sale_order.id if sale_order else 'None'}")
            
            if not sale_order:
                continue
            
            # ========================================
            # CHECK IF THIS SALE ORDER IS ALREADY PROCESSED
            # ========================================
            if sale_order.id in processed_sale_orders:
                print(f"SKIPPING - Sale Order {sale_order.id} already processed for this date range")
                continue
            
            # Mark this sale order as processed
            processed_sale_orders.add(sale_order.id)
            
            # Get sale order lines (Odoo 18: 'consu', 'service', 'combo')
            sale_lines = sale_order.order_line.filtered(
                lambda l: l.product_id and l.product_id.type in ['consu', 'service', 'combo']
            )
            if not sale_lines:
                continue
            
            for line in sale_lines:
                print(f"Processing Sale Order Line: {line}")
                vals = self._compute_fitting_metrics(appointment, line)
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
            raise ValidationError(_('No fitting data with sale orders found for the selected date range.'))
        
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
            })
            report_records.append(region_vals)
        
        if report_records:
            self.create(report_records)
        return {'type': 'ir.actions.client', 'tag': 'reload'}
    
    def _compute_fitting_metrics(self, appointment, sale_line):
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
        vals['client_code'] = appointment.patient_id.ref
        vals['client_name'] = appointment.patient_id.name
        vals['client_type'] = self._get_client_type(appointment)
        vals['sale_order_id'] = appointment.sale_order_id.id
        vals['sale_order_line_id'] = sale_line.id
        vals['product_id'] = sale_line.product_id.id
        vals['equipment_type'] = sale_line.product_id.categ_id.name or 'Accessories'
        vals['quantity'] = int(sale_line.product_uom_qty) if sale_line.product_uom_qty else 1
        vals['unit_price'] = sale_line.price_unit or sale_line.product_id.lst_price or 0.0
        discount_percentage = sale_line.discount or 0.0
        vals['discount'] = discount_percentage
        subtotal = vals['unit_price'] * vals['quantity']
        discount_amount = subtotal * (discount_percentage / 100)
        vals['discount_amount'] = discount_amount
        vals['subtotal'] = subtotal - discount_amount
        vals['gross'] = subtotal
        vals['total_amt_receivable'] = vals['subtotal']
        vals['weekly_target'] = self._get_weekly_target(appointment.clinic_id)
        
        # ========================================
        # ADD APPOINTMENT STATUS
        # ========================================
        vals['status'] = appointment.status
        
        # ========================================
        # GET SERIAL NUMBERS FROM DELIVERY
        # ========================================
        serial_numbers = self._get_serial_numbers(sale_line)
        vals['serial_numbers'] = serial_numbers
        
        return vals
    
    # def _get_serial_numbers(self, sale_order):
    #     """Get serial numbers from the delivery (stock picking)"""
    #     serial_numbers = []
        
    #     if sale_order:
    #         # Find the delivery/picking for this sale order
    #         pickings = self.env['stock.picking'].search([
    #             ('origin', '=', sale_order.name),
    #             ('state', 'in', ['assigned', 'done'])
    #         ], limit=1)
            
    #         if pickings:
    #             # Get all move lines with serial numbers
    #             for move_line in pickings.move_line_ids:
    #                 if move_line.lot_id and move_line.lot_id.name:
    #                     serial_numbers.append(move_line.lot_id.name)
        
    #     return ', '.join(serial_numbers) if serial_numbers else ''

    def _get_serial_numbers(self, sale_line):
        """Get serial numbers from stock moves linked to this sale order line."""

        serial_numbers = []

        if not sale_line:
            return ''

        # Find stock moves created from this specific sale order line
        moves = self.env['stock.move'].search([
            ('sale_line_id', '=', sale_line.id),
            ('state', '!=', 'cancel'),
        ])

        for move in moves:
            for move_line in move.move_line_ids:
                if move_line.lot_id and move_line.lot_id.name:
                    serial_numbers.append(move_line.lot_id.name)

        # Remove duplicates while preserving order
        serial_numbers = list(dict.fromkeys(serial_numbers))

        return ', '.join(serial_numbers) if serial_numbers else ''
    
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
        
        for appointment in appointments:
            sale_order = appointment.sale_order_id
            if not sale_order:
                continue
            sale_lines = sale_order.order_line.filtered(
                lambda l: l.product_id and l.product_id.type in ['consu', 'service', 'combo']
            )
            for line in sale_lines:
                vals = self._compute_fitting_metrics(appointment, line)
                for key, value in vals.items():
                    if key in numeric_fields and value is not None:
                        aggregated[key] = aggregated.get(key, 0) + value
        
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