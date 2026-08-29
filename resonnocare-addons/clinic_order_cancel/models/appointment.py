# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    appointment_id = fields.Many2one(
        'resonnocare.appointment',
        string='Appointment',
        help='Appointment linked to this sale order'
    )
    
    is_return_order = fields.Boolean(
        string='Is Return Order',
        default=False,
        help='True if this is a return order from cancellation'
    )
    
    is_exchange_order = fields.Boolean(
        string='Is Exchange Order',
        default=False,
        help='True if this is an exchange order'
    )
    
    original_sale_order_id = fields.Many2one(
        'sale.order',
        string='Original Sale Order',
        help='Original sale order if this is a return or exchange'
    )


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    appointment_id = fields.Many2one(
        'resonnocare.appointment',
        string='Appointment',
        help='Appointment linked to this invoice'
    )
    
    is_credit_note = fields.Boolean(
        string='Is Credit Note',
        default=False,
        help='True if this is a credit note from cancellation'
    )

class ResonnocareAppointment(models.Model):
    _inherit = 'resonnocare.appointment'


    child_appointment_ids = fields.One2many(
        "resonnocare.appointment",
        "parent_appointment_id",
        string="Child Appointments",
        help="Appointments created from this appointment"
    )

    # Root appointment (first in chain)
    root_appointment_id = fields.Many2one(
        "resonnocare.appointment",
        string="Root Appointment",
        compute="_compute_root_appointment",
        store=True,
        help="The first appointment in this patient journey"
    )

    # Previous appointment in journey
    previous_appointment_id = fields.Many2one(
        "resonnocare.appointment",
        string="Previous Appointment",
        compute="_compute_previous_next_appointments",
        store=True,
        help="Previous appointment in the patient journey"
    )

    # Next appointment in journey
    next_appointment_id = fields.Many2one(
        "resonnocare.appointment",
        string="Next Appointment",
        compute="_compute_previous_next_appointments",
        store=True,
        help="Next appointment in the patient journey"
    )

    # Journey position
    journey_position = fields.Integer(
        string="Journey Position",
        compute="_compute_journey_position",
        store=True,
        help="Position in the patient journey (1 = first)"
    )

    # Hierarchy level
    hierarchy_level = fields.Integer(
        string="Hierarchy Level",
        compute="_compute_hierarchy_level",
        store=True,
        help="Level in the hierarchy (0 = root)"
    )

    # Appointment category
    appointment_category = fields.Selection([
        ('service', 'Service/Diagnostic'),
        ('hearing_test', 'Hearing Test & Trial'),
        ('device_sale', 'Device Sale'),
        ('fitting', 'Fitting'),
        ('followup', 'Follow-up')
    ], string="Appointment Category", compute="_compute_appointment_category", store=True)


    # Add these compute methods in your ResonnocareAppointment class

    @api.depends('parent_appointment_id', 'parent_appointment_id.root_appointment_id')
    def _compute_root_appointment(self):
        for rec in self:
            if not rec.parent_appointment_id:
                rec.root_appointment_id = rec.id
            else:
                current = rec
                while current.parent_appointment_id:
                    current = current.parent_appointment_id
                rec.root_appointment_id = current.id

    @api.depends('parent_appointment_id', 'child_appointment_ids')
    def _compute_previous_next_appointments(self):
        for rec in self:
            # Previous appointment
            if rec.parent_appointment_id:
                rec.previous_appointment_id = rec.parent_appointment_id
            else:
                rec.previous_appointment_id = False
            
            # Next appointment (first child by creation date)
            if rec.child_appointment_ids:
                rec.next_appointment_id = rec.child_appointment_ids.sorted('create_date')[:1].id
            else:
                rec.next_appointment_id = False

    @api.depends('root_appointment_id', 'root_appointment_id.child_appointment_ids')
    def _compute_journey_position(self):
        for rec in self:
            if rec.root_appointment_id:
                # Get all appointments in journey
                all_appointments = rec.root_appointment_id | rec.root_appointment_id.child_appointment_ids
                sorted_appointments = all_appointments.sorted('create_date')
                positions = {appt.id: idx + 1 for idx, appt in enumerate(sorted_appointments)}
                rec.journey_position = positions.get(rec.id, 0)
            else:
                rec.journey_position = 1

    @api.depends('parent_appointment_id')
    def _compute_hierarchy_level(self):
        for rec in self:
            level = 0
            current = rec
            while current.parent_appointment_id:
                level += 1
                current = current.parent_appointment_id
            rec.hierarchy_level = level

    @api.depends('appointment_type_id', 'appointment_type_id.name')
    def _compute_appointment_category(self):
        for rec in self:
            type_name = (rec.appointment_type_id.name or '').lower()
            if 'service' in type_name or 'diagnostic' in type_name:
                rec.appointment_category = 'service'
            elif 'hearing' in type_name or 'test' in type_name or 'trial' in type_name:
                rec.appointment_category = 'hearing_test'
            elif 'device' in type_name or 'sale' in type_name:
                rec.appointment_category = 'device_sale'
            elif 'fitting' in type_name:
                rec.appointment_category = 'fitting'
            elif 'follow' in type_name or 'followup' in type_name:
                rec.appointment_category = 'followup'
            else:
                rec.appointment_category = False

    # Add these navigation methods in your ResonnocareAppointment class

    def action_view_parent(self):
        """Navigate to parent appointment"""
        self.ensure_one()
        if not self.parent_appointment_id:
            raise UserError("This appointment has no parent.")
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Parent Appointment',
            'res_model': 'resonnocare.appointment',
            'view_mode': 'form',
            'res_id': self.parent_appointment_id.id,
            'target': 'current',
        }

    def action_view_children(self):
        """View all child appointments"""
        self.ensure_one()
        if not self.child_appointment_ids:
            raise UserError("This appointment has no child appointments.")
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Child Appointments',
            'res_model': 'resonnocare.appointment',
            'view_mode': 'list,form',
            'domain': [('parent_appointment_id', '=', self.id)],
            'target': 'current',
            'context': {
                'default_parent_appointment_id': self.id,
            }
        }

    def action_view_previous(self):
        """Navigate to previous appointment in journey"""
        self.ensure_one()
        if not self.previous_appointment_id:
            raise UserError("This is the first appointment in the journey.")
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Previous Appointment',
            'res_model': 'resonnocare.appointment',
            'view_mode': 'form',
            'res_id': self.previous_appointment_id.id,
            'target': 'current',
        }

    def action_view_next(self):
        """Navigate to next appointment in journey"""
        self.ensure_one()
        if not self.next_appointment_id:
            raise UserError("This is the last appointment in the journey.")
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Next Appointment',
            'res_model': 'resonnocare.appointment',
            'view_mode': 'form',
            'res_id': self.next_appointment_id.id,
            'target': 'current',
        }

    def action_view_root(self):
        """Navigate to root appointment"""
        self.ensure_one()
        if not self.root_appointment_id:
            raise UserError("No root appointment found.")
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Root Appointment',
            'res_model': 'resonnocare.appointment',
            'view_mode': 'form',
            'res_id': self.root_appointment_id.id,
            'target': 'current',
        }





    def action_create_fitting_appointment(self):
        """Create a Fitting appointment with proper hierarchy"""
        self.ensure_one()
        
        fitting_type = self.env["resonnocare.appointment.type"].search(
            [("name", "ilike", "fitting"), ("active", "=", True)],
            limit=1,
        )
        if not fitting_type:
            raise UserError(
                "Appointment Type 'Fitting' is not configured. Please create/activate it in Masters."
            )
        
        sale = self._get_effective_sale_order()
        if sale:
            minimum_required = (sale.amount_total or 0.0) * 0.30
            total_paid = self._get_total_paid_for_sale(sale)
            if total_paid < minimum_required:
                approved_request = self.env["resonnocare.advance.approval.request"].search(
                    [
                        ("sale_order_id", "=", sale.id),
                        ("state", "=", "approved"),
                    ],
                    order="id desc",
                    limit=1,
                )
                if not approved_request or not approved_request.requested_min_advance:
                    raise UserError(
                        "Fitting appointment cannot be created because paid advance is below the required threshold.\n"
                        f"Minimum Required (30%): {minimum_required:.2f}\n"
                        f"Currently Paid: {total_paid:.2f}\n\n"
                        "To continue with a lower advance, create and get approval for a Min Advance Request from this Appointment or related Sale Order."
                    )
                if total_paid < approved_request.requested_min_advance:
                    raise UserError(
                        "Min Advance Request is approved, but paid amount is still below the approved minimum.\n"
                        f"Approved Minimum Advance: {approved_request.requested_min_advance:.2f}\n"
                        f"Paid: {total_paid:.2f}"
                    )
        
        # Get staff from original appointment
        audiologist_id = self.audiologist_id.id if self.audiologist_id else False
        technician_id = self.technician_id.id if self.technician_id else False
        
        # Calculate start time
        now = fields.Datetime.now()
        minutes = (now.minute // 5) * 5
        start_time = now.replace(minute=minutes, second=0, microsecond=0)
        appointment_start_time = start_time.hour + (start_time.minute / 60.0)
        
        # Create the fitting appointment with proper link
        fitting_appointment = self.env["resonnocare.appointment"].create({
            'parent_appointment_id': self.id,  # Link to original appointment
            'patient_id': self.patient_id.id,
            'clinic_id': self.clinic_id.id,
            'appointment_type_id': fitting_type.id,
            'sale_type': 'device',
            'sale_order_id': self.sale_order_id.id,
            'appointment_date': fields.Date.today(),
            'appointment_start_time': appointment_start_time,
            'audiologist_id': audiologist_id,
            'technician_id': technician_id,
            'source': self.source,
            'status': 'draft',
            'notes': f"Fitting appointment created from {self.appointment_id or self.name}",
            'name': f"Fitting - {self.patient_id.name}",
        })
        
        # Return to open the newly created fitting appointment
        return {
            "type": "ir.actions.act_window",
            "name": "Fitting Appointment",
            "res_model": "resonnocare.appointment",
            "view_mode": "form",
            "res_id": fitting_appointment.id,
            "target": "current",
        }



    # Add these methods in your ResonnocareAppointment class

    def action_create_hearing_test_appointment(self):
        """Create a Hearing Test & Trial appointment"""
        self.ensure_one()
        return self._create_child_appointment('hearing_test')

    def action_create_device_sale_appointment(self):
        """Create a Device Sale appointment"""
        self.ensure_one()
        return self._create_child_appointment('device_sale')

    def action_create_followup_appointment(self):
        """Create a Follow-up appointment"""
        self.ensure_one()
        return self._create_child_appointment('followup')

    def _create_child_appointment(self, appointment_type_key):
        """Generic method to create child appointments with hierarchy"""
        self.ensure_one()
        
        # Map appointment type key to actual appointment type
        type_mapping = {
            'hearing_test': ['Hearing Test', 'Test', 'Trial'],
            'device_sale': ['Device Sale', 'Device', 'Sale'],
            'fitting': ['Fitting'],
            'followup': ['Follow-up', 'Followup', 'Follow'],
        }
        
        # Find or create appointment type
        search_domains = []
        for keyword in type_mapping.get(appointment_type_key, []):
            search_domains.append(('name', 'ilike', keyword))
        
        if search_domains:
            domain = []
            for i, _ in enumerate(search_domains):
                if i > 0:
                    domain.append('|')
                domain.append(search_domains[i])
            
            app_type = self.env['resonnocare.appointment.type'].search(domain, limit=1)
        else:
            app_type = False
        
        if not app_type:
            type_name = appointment_type_key.replace('_', ' ').title()
            app_type = self.env['resonnocare.appointment.type'].create({
                'name': type_name,
                'code': f"APT-{appointment_type_key.upper()}",
                'sequence': 10,
                'active': True,
                'duration': 30,
                'sale_type': 'device' if appointment_type_key in ['device_sale', 'fitting'] else 'service',
            })
        
        # Calculate start time
        now = fields.Datetime.now()
        minutes = (now.minute // 5) * 5
        start_time = now.replace(minute=minutes, second=0, microsecond=0)
        appointment_start_time = start_time.hour + (start_time.minute / 60.0)
        
        # Determine sale type
        sale_type = 'device' if appointment_type_key in ['device_sale', 'fitting'] else 'service'
        
        # Create child appointment with hierarchy
        child_appointment = self.env['resonnocare.appointment'].create({
            'parent_appointment_id': self.id,
            'patient_id': self.patient_id.id,
            'clinic_id': self.clinic_id.id,
            'appointment_type_id': app_type.id,
            'appointment_date': fields.Date.today(),
            'appointment_start_time': appointment_start_time,
            'sale_type': sale_type,
            'audiologist_id': self.audiologist_id.id if self.audiologist_id else False,
            'technician_id': self.technician_id.id if self.technician_id else False,
            'source': self.source,
            'status': 'draft',
            'sale_order_id': self.sale_order_id.id if self.sale_order_id else False,
            'notes': f"Created from {self.appointment_id or self.name}",
            'name': f"{appointment_type_key.replace('_', ' ').title()} - {self.patient_id.name}",
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': f"{appointment_type_key.replace('_', ' ').title()} Appointment",
            'res_model': 'resonnocare.appointment',
            'view_mode': 'form',
            'res_id': child_appointment.id,
            'target': 'current',
        }
    # ========================================
    # INVOICE RELATIONSHIP
    # ========================================
    invoice_ids = fields.One2many(
        'account.move',
        'appointment_id',
        string='Invoices',
        help='All invoices linked to this appointment'
    )
    
    # ========================================
    # CANCELLATION FIELDS
    # ========================================
    original_appointment_id = fields.Many2one(
        'resonnocare.appointment',
        string='Original Appointment',
        help='Reference to the original appointment being cancelled'
    )
    
    cancellation_appointment_ids = fields.One2many(
        'resonnocare.appointment',
        'original_appointment_id',
        string='Cancellation Appointments',
        help='List of cancellation appointments created from this appointment'
    )
    
    return_order_id = fields.Many2one(
        'sale.order',
        string='Return Order',
        help='Return order created for this cancellation'
    )
    
    credit_note_id = fields.Many2one(
        'account.move',
        string='Credit Note',
        help='Credit note created for this cancellation'
    )
    
    cancellation_processed = fields.Boolean(
        string='Cancellation Processed',
        default=False,
        help='Indicates if the cancellation has been fully processed'
    )
    
    cancellation_status = fields.Selection([
        ('pending', 'Pending'),
        ('order_cancelled', 'Order Cancelled'),
        ('return_created', 'Return Created'),
        ('credit_note_generated', 'Credit Note Generated'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ], string='Cancellation Status', default='pending')
    
    cancellation_date = fields.Datetime(
        string='Cancellation Date',
        help='Date when cancellation was processed'
    )
    
    cancellation_reason = fields.Text(
        string='Cancellation Reason',
        help='Reason for cancellation'
    )
    
    cancellation_amount = fields.Float(
        string='Cancellation Amount',
        digits=(16, 2),
        help='Total amount cancelled'
    )
    
    has_cancellation_appointment = fields.Boolean(
        string='Has Cancellation Appointment',
        compute='_compute_has_cancellation_appointment',
        store=True,
    )
    
    # ========================================
    # READONLY FIELDS FROM ORIGINAL APPOINTMENT
    # ========================================
    original_patient_id = fields.Many2one(
        'res.partner',
        string='Original Patient',
        related='original_appointment_id.patient_id',
        store=True,
        readonly=True,
    )
    
    original_patient_name = fields.Char(
        string='Original Patient Name',
        related='original_appointment_id.patient_id.name',
        store=True,
        readonly=True,
    )
    
    original_appointment_date = fields.Date(
        string='Original Appointment Date',
        related='original_appointment_id.appointment_date',
        store=True,
        readonly=True,
    )
    
    original_clinic_name = fields.Char(
        string='Original Clinic',
        related='original_appointment_id.clinic_id.name',
        store=True,
        readonly=True,
    )
    
    original_audiologist = fields.Char(
        string='Original Audiologist',
        related='original_appointment_id.audiologist_id.name',
        store=True,
        readonly=True,
    )
    
    original_technician = fields.Char(
        string='Original Technician',
        related='original_appointment_id.technician_id.name',
        store=True,
        readonly=True,
    )
    
    original_device_lines = fields.Text(
        string='Original Devices',
        compute='_compute_original_device_lines',
        store=True,
        readonly=True,
    )
    
    original_diagnostic_tests = fields.Text(
        string='Original Diagnostic Tests',
        compute='_compute_original_diagnostic_tests',
        store=True,
        readonly=True,
    )
    
    original_sale_order_amount = fields.Monetary(
        string='Original Sale Order Amount',
        related='original_appointment_id.sale_order_id.amount_total',
        store=True,
        readonly=True,
    )
    
    original_sale_order_name = fields.Char(
        string='Original Sale Order',
        related='original_appointment_id.sale_order_id.name',
        store=True,
        readonly=True,
    )
    
    original_invoice_names = fields.Text(
        string='Original Invoices',
        compute='_compute_original_invoice_names',
        store=True,
        readonly=True,
    )
    
    original_invoice_total = fields.Monetary(
        string='Original Invoice Total',
        compute='_compute_original_invoice_total',
        store=True,
        readonly=True,
    )
    
    # ========================================
    # EXCHANGE FIELDS
    # ========================================
    exchange_order_id = fields.Many2one(
        'sale.order',
        string='Exchange Order',
        help='New sale order created for exchange'
    )
    
    exchange_processed = fields.Boolean(
        string='Exchange Processed',
        default=False,
        help='Indicates if the exchange has been fully processed'
    )
    
    exchange_status = fields.Selection([
        ('pending', 'Pending'),
        ('return_created', 'Return Created'),
        ('new_order_created', 'New Order Created'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ], string='Exchange Status', default='pending')
    
    exchange_amount_difference = fields.Monetary(
        string='Exchange Amount Difference',
        help='Difference between return value and new order value'
    )
    
    exchange_reason = fields.Text(
        string='Exchange Reason',
        help='Reason for exchange'
    )
    
    exchange_product_ids = fields.Many2many(
        'product.product',
        string='Exchange Products',
        help='Products selected for exchange'
    )
    
    exchange_return_order_id = fields.Many2one(
        'sale.order',
        string='Exchange Return Order',
        help='Return order created for exchange'
    )
    
    exchange_credit_note_id = fields.Many2one(
        'account.move',
        string='Exchange Credit Note',
        help='Credit note created for exchange'
    )

    # Add these fields to the appointment model if not already present
    parent_appointment_id = fields.Many2one(
        'resonnocare.appointment',
        string='Original Appointment',
        ondelete='set null',
        help='Reference to the original appointment that created this fitting appointment'
    )

    fitting_appointment_ids = fields.One2many(
        'resonnocare.appointment',
        'parent_appointment_id',
        string='Fitting Appointments',
        help='List of fitting appointments created from this appointment'
    )

    fitting_device_line_ids = fields.One2many(
        'resonnocare.appointment.device.line',
        related='parent_appointment_id.device_sale_line_ids',
        string='Fitting Devices',
        readonly=True,
    )

    def action_view_fitting_appointments(self):
        """Smart button to view fitting appointments"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Fitting Appointments',
            'res_model': 'resonnocare.appointment',
            'view_mode': 'list,form',
            'domain': [('parent_appointment_id', '=', self.id)],
            'target': 'current',
            'context': {
                'default_parent_appointment_id': self.id,
            }
        }
    
    @api.depends('original_appointment_id', 'original_appointment_id.invoice_ids')
    def _compute_original_invoice_names(self):
        for record in self:
            if record.original_appointment_id and record.original_appointment_id.invoice_ids:
                invoices = record.original_appointment_id.invoice_ids.filtered(
                    lambda inv: inv.state == 'posted'
                )
                record.original_invoice_names = '\n'.join(invoices.mapped('name'))
            else:
                record.original_invoice_names = ''
    
    @api.depends('original_appointment_id', 'original_appointment_id.invoice_ids')
    def _compute_original_invoice_total(self):
        for record in self:
            if record.original_appointment_id and record.original_appointment_id.invoice_ids:
                invoices = record.original_appointment_id.invoice_ids.filtered(
                    lambda inv: inv.state == 'posted'
                )
                record.original_invoice_total = sum(invoices.mapped('amount_total'))
            else:
                record.original_invoice_total = 0.0
    
    @api.depends('original_appointment_id')
    def _compute_original_device_lines(self):
        for record in self:
            if record.original_appointment_id and record.original_appointment_id.device_sale_line_ids:
                lines = []
                for line in record.original_appointment_id.device_sale_line_ids:
                    lines.append(f"{line.product_id.name} x {line.product_uom_qty}")
                record.original_device_lines = '\n'.join(lines)
            else:
                record.original_device_lines = ''
    
    @api.depends('original_appointment_id')
    def _compute_original_diagnostic_tests(self):
        for record in self:
            if record.original_appointment_id and record.original_appointment_id.diagnostic_item_ids:
                tests = record.original_appointment_id.diagnostic_item_ids.mapped('name')
                record.original_diagnostic_tests = '\n'.join(tests)
            else:
                record.original_diagnostic_tests = ''
    
    @api.depends('cancellation_appointment_ids')
    def _compute_has_cancellation_appointment(self):
        for record in self:
            record.has_cancellation_appointment = bool(record.cancellation_appointment_ids)

    # ========================================
    # CREATE CANCELLATION APPOINTMENT
    # ========================================
    def action_create_cancel_appointment(self):
        """Create a new Order Cancel appointment from this appointment"""
        self.ensure_one()
        
        # Check if this appointment already has a sale order
        if not self.sale_order_id:
            raise ValidationError("This appointment has no sale order to cancel.")
        
        # Check if cancellation already exists
        existing_cancel = self.cancellation_appointment_ids.filtered(
            lambda a: a.cancellation_processed == False
        )
        
        if existing_cancel:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Existing Cancellation',
                'res_model': 'resonnocare.appointment',
                'view_mode': 'form',
                'res_id': existing_cancel[0].id,
                'target': 'current',
            }
        
        # Create the cancellation appointment
        cancel_appointment = self._create_order_cancel_appointment()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cancellation Appointment',
            'res_model': 'resonnocare.appointment',
            'view_mode': 'form',
            'res_id': cancel_appointment.id,
            'target': 'current',
        }
    
    def _create_order_cancel_appointment(self):
        """Create a new Order Cancel appointment linked to this appointment"""
        self.ensure_one()
        
        # Find or create Order Cancel appointment type
        cancel_type = self.env['resonnocare.appointment.type'].search([
            ('name', '=', 'Order Cancel')
        ], limit=1)
        
        if not cancel_type:
            # Create the appointment type if it doesn't exist
            cancel_type = self.env['resonnocare.appointment.type'].create({
                'name': 'Order Cancel',
                'code': 'APT-0020',
                'sequence': 10,
                'active': True,
                'duration': 5,
                'sale_type': 'device',
            })
        
        # Calculate start time (current time rounded to nearest 5 minutes)
        now = fields.Datetime.now()
        minutes = (now.minute // 5) * 5
        start_time = now.replace(minute=minutes, second=0, microsecond=0)
        
        # Create the cancellation appointment
        cancel_appointment = self.env['resonnocare.appointment'].create({
            'clinic_id': self.clinic_id.id,
            'patient_id': self.patient_id.id,
            'appointment_type_id': cancel_type.id,
            'appointment_date': fields.Date.today(),
            'appointment_start_time': start_time.hour + (start_time.minute / 60.0),
            'source': self.source,
            'status': 'draft',
            'original_appointment_id': self.id,  # Link back to original
            'sale_order_id': self.sale_order_id.id,  # Copy sale order
            'cancellation_amount': self.sale_order_id.amount_total if self.sale_order_id else 0.0,
            'notes': f"Cancellation of appointment {self.appointment_id or self.name}",
            'audiologist_id': self.audiologist_id.id if self.audiologist_id else False,
            'technician_id': self.technician_id.id if self.technician_id else False,
        })
        
        _logger.info(f"Created cancellation appointment: {cancel_appointment.appointment_id or cancel_appointment.name}")
        
        return cancel_appointment

    # ========================================
    # PROCESS CANCELLATION
    # ========================================
    def action_process_cancellation(self):
        """Process the cancellation from the Order Cancel appointment"""
        self.ensure_one()
        
        if self.appointment_type_id.name != 'Order Cancel':
            raise ValidationError("This is not a cancellation appointment.")
        
        if self.cancellation_processed:
            raise ValidationError("This cancellation has already been processed.")
        
        if not self.original_appointment_id:
            raise ValidationError("No original appointment linked to this cancellation.")
        
        original = self.original_appointment_id
        
        try:
            original._fetch_and_link_invoices()
            # Step 1: Create return order FIRST (before cancelling sale order)
            original._create_return_order()
            
            # Step 2: Generate credit notes for all invoices
            original._create_credit_notes()
            
            # Step 3: Cancel the sale order (after return is created)
            original._cancel_sale_order()
            
            # Step 4: Mark this cancellation as processed
            self.cancellation_processed = True
            self.cancellation_status = 'completed'
            self.cancellation_date = fields.Datetime.now()
            self.sale_order_id = original.sale_order_id.id
            self.return_order_id = original.return_order_id.id
            
            # Link credit note
            if original.credit_note_id:
                self.credit_note_id = original.credit_note_id.id
            
            self.cancellation_amount = original.cancellation_amount
            
            # Step 5: Mark original as cancelled
            original.status = 'cancelled'
            
            _logger.info(
                f"Cancellation processed for appointment {self.id}: "
                f"Original: {original.appointment_id or original.name}, "
                f"Sale Order: {original.sale_order_id.name if original.sale_order_id else 'N/A'}, "
                f"Return Order: {self.return_order_id.name if self.return_order_id else 'N/A'}, "
                f"Credit Note: {self.credit_note_id.name if self.credit_note_id else 'N/A'}"
            )
            
        except Exception as e:
            _logger.error(f"Error processing cancellation: {str(e)}")
            self.cancellation_status = 'failed'
            raise UserError(f"Cancellation failed: {str(e)}")
    
    # ========================================
    # CANCELLATION HELPER METHODS
    # ========================================
    def _cancel_sale_order(self):
        """Cancel the linked sale order"""
        if not self.sale_order_id:
            return
            
        if self.sale_order_id.state in ['sale', 'done']:
            try:
                self.cancellation_amount = self.sale_order_id.amount_total
                self.sale_order_id.action_cancel()
                self.cancellation_status = 'order_cancelled'
                _logger.info(f"Sale order {self.sale_order_id.name} cancelled successfully")
            except Exception as e:
                raise UserError(f"Failed to cancel sale order: {str(e)}")
    
    def _create_return_order(self):
        """Create a return order for delivered products with serial numbers"""
        if not self.sale_order_id:
            return
            
        # Get done pickings from the sale order
        pickings = self.sale_order_id.picking_ids.filtered(lambda p: p.state == 'done')
        
        if not pickings:
            _logger.warning("No delivered pickings found for return")
            return
            
        try:
            return_picking_ids = []
            
            # For each delivered picking, create a return
            for picking in pickings:
                # Get the serial numbers from the original delivery
                serial_map = {}
                for move_line in picking.move_line_ids:
                    if move_line.lot_id and move_line.product_id:
                        key = move_line.product_id.id
                        if key not in serial_map:
                            serial_map[key] = []
                        if move_line.lot_id.name not in serial_map[key]:
                            serial_map[key].append(move_line.lot_id.name)
                
                # Create return wizard
                return_wizard = self.env['stock.return.picking'].with_context(
                    active_id=picking.id,
                    active_model='stock.picking'
                ).create({
                    'picking_id': picking.id,
                })
                
                # Set return quantities for all move lines
                for line in return_wizard.product_return_moves:
                    if line.move_id and line.move_id.product_uom_qty > 0:
                        line.quantity = line.move_id.product_uom_qty
                        line.to_refund = True
                
                # Process the return if there are any moves
                if return_wizard.product_return_moves:
                    result = return_wizard.action_create_returns()
                    
                    if result and 'res_id' in result:
                        return_picking = self.env['stock.picking'].browse(result['res_id'])
                        
                        # Now assign serial numbers to the return picking move lines
                        if serial_map:
                            for move_line in return_picking.move_line_ids:
                                product_id = move_line.product_id.id
                                if product_id in serial_map and serial_map[product_id]:
                                    # Find the lot/serial record
                                    lot_name = serial_map[product_id][0]
                                    lot = self.env['stock.lot'].search([
                                        ('product_id', '=', product_id),
                                        ('name', '=', lot_name)
                                    ], limit=1)
                                    if lot:
                                        move_line.lot_id = lot.id
                                        # Remove used serial from map
                                        serial_map[product_id].pop(0)
                                        if not serial_map[product_id]:
                                            del serial_map[product_id]
                                        _logger.info(f"Assigned serial {lot_name} to return move line")
                        
                        return_picking.action_confirm()
                        return_picking.action_assign()
                        return_picking.button_validate()
                        return_picking_ids.append(return_picking.id)
                        
                        _logger.info(f"Return picking {return_picking.name} created successfully")
                    else:
                        _logger.warning(f"No return pickings created for picking {picking.name}")
                else:
                    _logger.warning(f"No returnable products found in picking {picking.name}")
            
            if return_picking_ids:
                # Create return sale order
                self._create_return_sale_order()
                self.cancellation_status = 'return_created'
                _logger.info(f"Return order created successfully for sale {self.sale_order_id.name}")
            else:
                _logger.warning("No return pickings were created")
                
        except Exception as e:
            _logger.error(f"Failed to create return: {str(e)}")
            raise UserError(f"Failed to create return order: {str(e)}")
    
    def _create_return_sale_order(self):
        """Create a negative sale order for the return"""
        if not self.sale_order_id:
            return
            
        # Create a return sale order
        return_so = self.env['sale.order'].create({
            'partner_id': self.sale_order_id.partner_id.id,
            'user_id': self.sale_order_id.user_id.id,
            'pricelist_id': self.sale_order_id.pricelist_id.id,
            'client_order_ref': f"Return for {self.sale_order_id.name}",
            'origin': self.sale_order_id.name,
            'clinic_id': self.clinic_id.id if self.clinic_id else False,
            'is_return_order': True,  # ADD THIS
            'original_sale_order_id': self.sale_order_id.id,  # ADD THIS
        })
        
        # Add negative order lines for returned products
        for line in self.sale_order_id.order_line:
            if line.product_id:
                self.env['sale.order.line'].create({
                    'order_id': return_so.id,
                    'product_id': line.product_id.id,
                    'product_uom_qty': -line.product_uom_qty,
                    'product_uom': line.product_uom.id,
                    'price_unit': line.price_unit,
                    'tax_id': [(6, 0, line.tax_id.ids)],
                    'discount': line.discount,
                })
        
        self.return_order_id = return_so.id
        return_so.action_confirm()
        _logger.info(f"Return sale order {return_so.name} created")
    
    def _create_credit_notes(self):
        """Generate credit notes for all posted invoices"""
        if not self.invoice_ids:
            return
            
        posted_invoices = self.invoice_ids.filtered(lambda inv: inv.state == 'posted')
        
        if not posted_invoices:
            _logger.warning("No posted invoices found, skipping credit notes")
            return
        
        credit_notes = self.env['account.move']
        
        for invoice in posted_invoices:
            try:
                # Create credit note using default_values_list
                credit_note = invoice._reverse_moves(
                    default_values_list=[{
                        'ref': f"Credit note for {invoice.name} - {self.appointment_id or self.name}",
                        'invoice_date': fields.Date.today(),
                        'clinic_id': self.clinic_id.id if self.clinic_id else False,
                    }]
                )
                
                # Post the credit note
                credit_note.action_post()
                credit_notes |= credit_note
                
                _logger.info(f"Credit note {credit_note.name} generated successfully")
                
            except Exception as e:
                _logger.error(f"Failed to create credit note for invoice {invoice.name}: {str(e)}")
                # Continue with other invoices
        
        # Link credit note to appointment
        if credit_notes:
            self.credit_note_id = credit_notes[0].id
            self.cancellation_status = 'credit_note_generated'
    
    # ========================================
    # EXCHANGE METHODS
    # ========================================
    def action_create_exchange_wizard(self):
        """Open wizard to create exchange from cancellation appointment"""
        self.ensure_one()
        
        if self.appointment_type_id.name != 'Order Cancel':
            raise ValidationError("Exchange can only be created from a cancellation appointment.")
        
        if self.exchange_processed:
            raise ValidationError("Exchange has already been processed for this cancellation.")
        
        if not self.original_appointment_id:
            raise ValidationError("No original appointment linked to this cancellation.")
        
        # Open the exchange wizard
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Exchange',
            'res_model': 'resonnocare.exchange.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_cancellation_appointment_id': self.id,
                'default_original_appointment_id': self.original_appointment_id.id,
                'default_patient_id': self.patient_id.id,
                'default_clinic_id': self.clinic_id.id,
                'default_return_order_id': self.return_order_id.id,
            }
        }
    
    def process_exchange(self, exchange_data):
        """Process the exchange from the wizard data"""
        self.ensure_one()
        
        if self.exchange_processed:
            raise ValidationError("Exchange already processed.")
        
        original = self.original_appointment_id
        
        try:
            # Step 1: Create return for the original products (already done in cancellation)
            if not self.return_order_id:
                original._create_return_order()
                self.return_order_id = original.return_order_id.id
            
            # Step 2: Create credit note for returned products
            if not self.credit_note_id:
                original._create_credit_notes()
                if original.credit_note_id:
                    self.credit_note_id = original.credit_note_id.id
                    self.exchange_credit_note_id = original.credit_note_id.id
            
            # Step 3: Create new sale order for exchange products
            new_order = self._create_exchange_sale_order(exchange_data)
            self.exchange_order_id = new_order.id
            
            # Step 4: Create delivery for new order
            self._create_exchange_delivery(new_order)
            
            # Step 5: Create invoice for the difference if any
            if exchange_data.get('amount_difference', 0) > 0:
                self._create_exchange_invoice(new_order, exchange_data.get('amount_difference', 0))
            
            # Step 6: Update exchange status
            self.exchange_processed = True
            self.exchange_status = 'completed'
            self.exchange_amount_difference = exchange_data.get('amount_difference', 0)
            self.exchange_reason = exchange_data.get('reason', '')
            
            # Step 7: Link exchange products
            if exchange_data.get('product_ids'):
                self.exchange_product_ids = [(6, 0, exchange_data.get('product_ids'))]
            
            _logger.info(
                f"Exchange processed for appointment {self.id}: "
                f"Original: {original.appointment_id or original.name}, "
                f"New Order: {new_order.name}, "
                f"Amount Difference: {self.exchange_amount_difference}"
            )
            
        except Exception as e:
            _logger.error(f"Error processing exchange: {str(e)}")
            self.exchange_status = 'failed'
            raise UserError(f"Exchange failed: {str(e)}")
    
    def _create_exchange_sale_order(self, exchange_data):
        """Create a new sale order for exchange products"""
        original_order = self.original_appointment_id.sale_order_id
        
        if not original_order:
            raise UserError("No original sale order found.")
        
        # Create new sale order
        new_order = self.env['sale.order'].create({
            'partner_id': original_order.partner_id.id,
            'user_id': original_order.user_id.id,
            'pricelist_id': original_order.pricelist_id.id,
            'client_order_ref': f"Exchange for {original_order.name}",
            'origin': original_order.name,
            'clinic_id': self.clinic_id.id if self.clinic_id else False,
            'note': f"Exchange order created from cancellation {self.name}",
            # 'appointment_id': self.original_appointment_id.id,  # REMOVE THIS LINE
            'is_exchange_order': True,  # ADD THIS
            'original_sale_order_id': original_order.id,  # ADD THIS
        })
        
        # Add exchange products as order lines
        for product_data in exchange_data.get('products', []):
            product = self.env['product.product'].browse(product_data['product_id'])
            
            # Get price from original order or pricelist
            price = product_data.get('price', product.lst_price)
            
            self.env['sale.order.line'].create({
                'order_id': new_order.id,
                'product_id': product.id,
                'product_uom_qty': product_data.get('quantity', 1),
                'product_uom': product.uom_id.id,
                'price_unit': price,
                'tax_id': [(6, 0, product.taxes_id.ids)],
            })
        
        # Confirm the order
        new_order.action_confirm()
        
        _logger.info(f"Exchange sale order {new_order.name} created")
        return new_order
    
    def _create_exchange_delivery(self, new_order):
        """Create delivery for the exchange order"""
        try:
            # Find or create picking for the new order
            pickings = new_order.picking_ids
            
            if not pickings:
                # Get default picking type
                picking_type = self.env['stock.picking.type'].search([
                    ('code', '=', 'outgoing'),
                    ('warehouse_id.company_id', '=', self.env.company.id)
                ], limit=1)
                
                if not picking_type:
                    picking_type = self.env.ref('stock.picking_type_out')
                
                # Create picking
                pickings = self.env['stock.picking'].create({
                    'partner_id': new_order.partner_id.id,
                    'picking_type_id': picking_type.id,
                    'location_id': picking_type.default_location_src_id.id or self.env.ref('stock.stock_location_stock').id,
                    'location_dest_id': new_order.partner_id.property_stock_customer.id,
                    'origin': new_order.name,
                    'sale_id': new_order.id,
                })
                
                # Create stock moves for order lines
                for line in new_order.order_line:
                    if line.product_id.type != 'service':
                        self.env['stock.move'].create({
                            'name': line.name,
                            'product_id': line.product_id.id,
                            'product_uom_qty': line.product_uom_qty,
                            'product_uom': line.product_uom.id,
                            'picking_id': pickings.id,
                            'location_id': picking_type.default_location_src_id.id or self.env.ref('stock.stock_location_stock').id,
                            'location_dest_id': new_order.partner_id.property_stock_customer.id,
                        })
            
            # Confirm and validate the picking
            for picking in pickings:
                if picking.state == 'draft':
                    picking.action_confirm()
                    picking.action_assign()
                    
                    # Check if all moves are available
                    if all(move.state == 'assigned' for move in picking.move_ids):
                        picking.button_validate()
                    else:
                        _logger.warning(f"Not all products available for exchange picking {picking.name}")
            
            _logger.info(f"Exchange delivery created for order {new_order.name}")
            
        except Exception as e:
            _logger.error(f"Failed to create exchange delivery: {str(e)}")
            # Don't fail the exchange if delivery fails, just log it
            _logger.warning(f"Delivery creation failed but exchange will continue: {str(e)}")
    
    def _create_exchange_invoice(self, new_order, amount_difference):
        """Create invoice for the amount difference in exchange"""
        try:
            # Create invoice for the difference
            invoice = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': new_order.partner_id.id,
                'invoice_date': fields.Date.today(),
                'invoice_origin': f"Exchange difference for {new_order.name}",
                'clinic_id': self.clinic_id.id if self.clinic_id else False,
                'invoice_line_ids': [(0, 0, {
                    'name': f"Exchange amount difference for {new_order.name}",
                    'price_unit': amount_difference,
                    'quantity': 1,
                    'product_id': self.env.ref('product.product_product_consultant').id,
                    'account_id': self.env['account.account'].search([('account_type', '=', 'income')], limit=1).id,
                })],
            })
            
            invoice.action_post()
            self.exchange_credit_note_id = invoice.id
            
            _logger.info(f"Exchange difference invoice {invoice.name} created for {amount_difference}")
            
        except Exception as e:
            _logger.error(f"Failed to create exchange invoice: {str(e)}")
            # Don't fail the exchange, just log the error
    
    # ========================================
    # SMART BUTTON METHODS
    # ========================================
    def action_view_sale_order(self):
        """Smart button to view sale order"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale Order',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'target': 'current',
        }
    
    def action_view_return_order(self):
        """Smart button to view return order"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Return Order',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'res_id': self.return_order_id.id,
            'target': 'current',
        }
    
    def action_view_credit_note(self):
        """Smart button to view credit note"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Credit Note',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.credit_note_id.id,
            'target': 'current',
        }
    
    def action_view_cancellation_appointments(self):
        """Smart button to view cancellation appointments"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cancellation Appointments',
            'res_model': 'resonnocare.appointment',
            'view_mode': 'list,form',
            'domain': [('original_appointment_id', '=', self.id)],
            'target': 'current',
            'context': {
                'default_original_appointment_id': self.id,
            }
        }
    
    def action_view_exchange_order(self):
        """Smart button to view exchange order"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Exchange Order',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'res_id': self.exchange_order_id.id,
            'target': 'current',
        }

    def _fetch_and_link_invoices(self):
        """Fetch all invoices from sale order and link them to appointment"""
        if not self.sale_order_id:
            return
        
        # Get all posted customer invoices from the sale order
        invoices = self.sale_order_id.invoice_ids.filtered(
            lambda inv: inv.move_type == 'out_invoice' and inv.state == 'posted'
        )
        
        if not invoices:
            _logger.warning(f"No posted invoices found for sale order {self.sale_order_id.name}")
            return
        
        # Link each invoice to this appointment
        for invoice in invoices:
            if invoice.appointment_id.id != self.id:
                invoice.sudo().write({
                    'appointment_id': self.id
                })
                _logger.info(f"Linked invoice {invoice.name} to appointment {self.id}")
        
        # Clear cache to refresh invoice_ids
        self.invalidate_recordset(['invoice_ids'])
        
        _logger.info(f"Linked {len(invoices)} invoices to appointment {self.id}")


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    appointment_id = fields.Many2one(
        'resonnocare.appointment',
        string='Appointment',
        help='Appointment linked to this invoice'
    )


# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class ResonnocareExchangeWizard(models.TransientModel):
    """Wizard for creating exchanges"""
    _name = 'resonnocare.exchange.wizard'
    _description = 'Exchange Wizard'
    
    cancellation_appointment_id = fields.Many2one(
        'resonnocare.appointment',
        string='Cancellation Appointment',
        required=True,
    )
    
    original_appointment_id = fields.Many2one(
        'resonnocare.appointment',
        string='Original Appointment',
        required=True,
    )
    
    patient_id = fields.Many2one(
        'res.partner',
        string='Patient',
        required=True,
    )
    
    clinic_id = fields.Many2one(
        'res.partner',
        string='Clinic',
        required=True,
    )
    
    return_order_id = fields.Many2one(
        'sale.order',
        string='Return Order',
        help='Return order from original sale',
    )
    
    exchange_line_ids = fields.One2many(
        'resonnocare.exchange.wizard.line',
        'wizard_id',
        string='Exchange Products',
    )
    
    amount_difference = fields.Monetary(
        string='Amount Difference',
        compute='_compute_amount_difference',
        store=True,
        help='Difference between return amount and new order amount',
    )
    
    reason = fields.Text(
        string='Exchange Reason',
        required=True,
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='clinic_id.currency_id',
        readonly=True,
    )
    
    return_amount = fields.Monetary(
        string='Return Amount',
        compute='_compute_amount_difference',
        store=True,
        help='Total amount of the original order being returned',
    )
    
    new_order_amount = fields.Monetary(
        string='New Order Amount',
        compute='_compute_amount_difference',
        store=True,
        help='Total amount of the new exchange order',
    )
    
    @api.depends('exchange_line_ids', 'exchange_line_ids.subtotal')
    def _compute_amount_difference(self):
        for wizard in self:
            # Get return amount from original order
            if wizard.cancellation_appointment_id and wizard.cancellation_appointment_id.original_appointment_id:
                original_order = wizard.cancellation_appointment_id.original_appointment_id.sale_order_id
                wizard.return_amount = original_order.amount_total if original_order else 0.0
            else:
                wizard.return_amount = 0.0
            
            # Calculate new order amount
            wizard.new_order_amount = sum(wizard.exchange_line_ids.mapped('subtotal'))
            
            # Calculate difference (negative means customer owes money, positive means refund)
            wizard.amount_difference = wizard.new_order_amount - wizard.return_amount
    
    def action_confirm_exchange(self):
        """Confirm and process the exchange"""
        self.ensure_one()
        
        if not self.exchange_line_ids:
            raise ValidationError("Please add at least one product for exchange.")
        
        # Prepare exchange data
        exchange_data = {
            'products': [{
                'product_id': line.product_id.id,
                'quantity': line.quantity,
                'price': line.price_unit,
            } for line in self.exchange_line_ids],
            'amount_difference': self.amount_difference,
            'reason': self.reason,
            'product_ids': self.exchange_line_ids.mapped('product_id').ids,
        }
        
        # Process the exchange
        try:
            self.cancellation_appointment_id.process_exchange(exchange_data)
            
            # Close wizard and show success message
            return {
                'type': 'ir.actions.act_window',
                'name': 'Exchange Processed',
                'res_model': 'resonnocare.appointment',
                'res_id': self.cancellation_appointment_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
            
        except Exception as e:
            raise UserError(f"Failed to process exchange: {str(e)}")


class ResonnocareExchangeWizardLine(models.TransientModel):
    """Lines for exchange wizard"""
    _name = 'resonnocare.exchange.wizard.line'
    _description = 'Exchange Wizard Line'
    
    wizard_id = fields.Many2one(
        'resonnocare.exchange.wizard',
        string='Wizard',
        required=True,
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        domain="[('sale_ok', '=', True)]",
    )
    
    quantity = fields.Float(
        string='Quantity',
        required=True,
        default=1.0,
    )
    
    price_unit = fields.Float(
        string='Price',
        required=True,
        default=0.0,
    )
    
    subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_subtotal',
        store=True,
    )
    
    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Set default price from product"""
        if self.product_id:
            self.price_unit = self.product_id.lst_price    