from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    notification_ids = fields.One2many('crm.lead.notification', 'lead_id', string='Notifications')
    last_notification_count = fields.Integer(string='Last Notification Count', compute='_compute_last_notification_count')
    
    def _compute_last_notification_count(self):
        for lead in self:
            lead.last_notification_count = len(lead.notification_ids)

    def action_view_notifications(self):
        """View notifications for this lead"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Notifications',
            'res_model': 'crm.lead.notification',
            'view_mode': 'list,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {'default_lead_id': self.id},
            'target': 'current',
        }

    @api.model
    def create(self, vals):
        """Override create to send notification for new lead"""
        lead = super(CrmLead, self).create(vals)
        
        # Send notification for new lead
        if lead.user_id:
            try:
                self.env['crm.lead.notification'].create_lead_notification(lead)
                _logger.info(f"Created notification for new lead: {lead.name}")
            except Exception as e:
                _logger.error(f"Error creating notification for lead {lead.name}: {e}")
        
        return lead
    
    def write(self, vals):
        for lead in self:
            old_stage = lead.stage_id
            
            # Check if stage is being changed
            if 'stage_id' in vals and lead.user_id:
                new_stage = self.env['crm.stage'].browse(vals['stage_id'])
                if old_stage != new_stage:
                    # Create notification for stage change
                    notification_obj = self.env['crm.lead.notification']
                    notification_obj.create_stage_change_notification(lead, old_stage, new_stage)
                    
                    # Also send email notification if configured
                    if lead.user_id.email:
                        self._send_email_notification(lead, old_stage, new_stage)
            
        return super(CrmLead, self).write(vals)

    def _send_email_notification(self, lead, old_stage, new_stage):
        """Send email notification for stage change"""
        template = self.env.ref('crm_lead_notification_bell.email_template_lead_notification', raise_if_not_found=False)
        if template and lead.user_id and lead.user_id.email:
            try:
                template.with_context(
                    old_stage=old_stage,
                    new_stage=new_stage
                ).send_mail(lead.id, force_send=False)
            except Exception as e:
                _logger.error(f"Failed to send email notification: {e}")


class ResUsers(models.Model):
    _inherit = 'res.users'

    crm_lead_stage_notification = fields.Boolean(
        string='Enable Stage Change Notifications',
        default=True
    )
    crm_lead_email_notification = fields.Boolean(
        string='Enable Email Notifications',
        default=False
    )          


class ResPartner(models.Model):
    _inherit = 'res.partner'

    notification_count = fields.Integer(
        string='Notification Count', 
        compute='_compute_notification_count'
    )
    
    def _compute_notification_count(self):
        for partner in self:
            try:
                partner.notification_count = self.env['crm.lead.notification'].sudo().search_count([
                    ('partner_id', '=', partner.id),
                    ('is_read', '=', False)
                ])
            except Exception:
                partner.notification_count = 0

    def action_view_notifications(self):
        """View notifications for this partner"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Notifications',
            'res_model': 'crm.lead.notification',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
            'target': 'current',
        }

    @api.model
    def create(self, vals):
        """Override create to send notification for new partner"""
        partner = super(ResPartner, self).create(vals)
        
        # Send notification for new partner (only for main partners, not contacts)
        if partner:
            try:
                self.env['crm.lead.notification'].create_partner_notification(partner)
                _logger.info(f"Notification created for partner: {partner.name}")
            except Exception as e:
                _logger.error(f"Error creating notification for partner {partner.id}: {e}")
        
        return partner
    

    