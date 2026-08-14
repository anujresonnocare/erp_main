from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.model_create_multi
    def create(self, vals_list):

        messages = super().create(vals_list)

        notification_obj = self.env['crm.lead.notification']

        for message in messages:
            try:

                # Only Log Notes
                if not (
                    message.message_type == 'comment'
                    and message.subtype_id
                    and message.subtype_id.internal
                ):
                    continue

                if not message.model or not message.res_id:
                    continue

                record = self.env[message.model].browse(message.res_id)

                if not record.exists():
                    continue

                record_name = (
                    record.display_name
                    if hasattr(record, 'display_name')
                    else f"{message.model},{message.res_id}"
                )

                notification_message = _(
                    "%s added a log note on %s"
                ) % (
                    message.author_id.name,
                    record_name
                )

                users = self.env['res.users']

                # Followers
                # for partner in record.message_partner_ids:
                #     users |= partner.user_ids

                # # Responsible User
                # if hasattr(record, 'user_id') and record.user_id:
                #     users |= record.user_id
                users = message.partner_ids.mapped('user_ids') - self.env.user
                # Don't notify current user
                # users -= self.env.user

                for user in users:

                    notification_obj.sudo().create({
                        'title': _('New Log Note'),
                        'message': notification_message,
                        'user_id': user.id,
                        'notification_type': 'log_note',
                        'model_name': message.model,
                        'record_id': message.res_id,
                        'record_name': record_name,
                    })

                    try:
                        user.notify_info(
                            message=notification_message,
                            title=_('New Log Note'),
                            sticky=False,
                        )
                    except Exception:
                        pass

            except Exception as e:
                _logger.exception(
                    "Log note notification failed: %s",
                    str(e)
                )

        return messages
    
class CrmLeadNotification(models.Model):
    _name = 'crm.lead.notification'
    _description = 'CRM Lead Notification'
    _order = 'create_date DESC'
    _rec_name = 'title'

    title = fields.Char(string='Title', required=True)
    message = fields.Text(string='Message', required=True)
    # Make lead_id optional (required=False)
    lead_id = fields.Many2one('crm.lead', string='Lead', ondelete='cascade', required=False)
    partner_id = fields.Many2one('res.partner', string='Customer', ondelete='cascade', required=False)
    user_id = fields.Many2one('res.users', string='User', required=True, default=lambda self: self.env.user)
    is_read = fields.Boolean(string='Read', default=False)
    notification_type = fields.Selection([
        ('stage_change', 'Stage Change'),
        ('lead_created', 'Lead Created'),
        ('partner_created', 'Customer Created'),
        ('log_note', 'Log Note'),
        ('assignment', 'Assignment'),
        ('system', 'System')
    ], string='Type', default='system')
    read_date = fields.Datetime(string='Read Date')
    create_date = fields.Datetime(string='Create Date', readonly=True, default=fields.Datetime.now)

    # Generic record information
    model_name = fields.Char()
    record_id = fields.Integer()
    record_name = fields.Char()



    def action_open_record(self):
        self.ensure_one()

        if not self.model_name or not self.record_id:
            return False

        return {
            'type': 'ir.actions.act_window',
            'res_model': self.model_name,
            'res_id': self.record_id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_mark_as_read(self):
        """Mark notifications as read"""
        for notification in self:
            notification.write({
                'is_read': True,
                'read_date': fields.Datetime.now()
            })
        return True

    @api.model
    def get_unread_count(self):
        """Get unread notification count for current user"""
        try:
            count = self.sudo().search_count([
                ('user_id', '=', self.env.user.id),
                ('is_read', '=', False)
            ])
            return count
        except Exception as e:
            _logger.error(f"Error getting unread count: {e}")
            return 0

    @api.model
    def get_recent_notifications(self, limit=20):
        notifications = self.search([
            ('user_id', '=', self.env.user.id)
        ], limit=limit)

        result = []

        for n in notifications:
            result.append({
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'is_read': n.is_read,
                'create_date': n.create_date.isoformat(),
                'type': n.notification_type,
                'model': n.model_name,
                'record_id': n.record_id,
                'record_name': n.record_name,
            })

        return result

    @api.model
    def create_lead_notification(self, lead):
        """Create notification for new lead"""
        if not lead or not lead.user_id:
            return False
            
        title = _("New Lead Created")
        message = _("New lead '%s' has been created") % lead.name
        
        try:
            notification = self.sudo().create({
                'title': title,
                'message': message,
                'lead_id': lead.id,
                'user_id': lead.user_id.id,
                'notification_type': 'lead_created',
                'is_read': False
            })
            
            # Send popup notification
            if lead.user_id.partner_id:
                try:
                    lead.user_id.notify_info(
                        message=message,
                        title=title,
                        sticky=False
                    )
                except:
                    pass
            
            return notification
        except Exception as e:
            _logger.error(f"Error creating lead notification: {e}")
            return False

    @api.model
    def create_partner_notification(self, partner):
        """Create notification when partner/customer is created"""
        if not partner:
            return False
        
        title = _("New Customer Created")
        message = _("New customer '%s' has been created") % (partner.display_name or partner.name)
        
        try:
            # Create without lead_id
            notification = self.sudo().create({
                'title': title,
                'message': message,
                'partner_id': partner.id,
                'user_id': self.env.user.id,
                'notification_type': 'partner_created',
                'is_read': False
            })
            
            _logger.info(f"Partner notification created successfully: {notification.id}")
            
            # Send popup notification
            if self.env.user.partner_id:
                try:
                    self.env.user.notify_info(
                        message=message,
                        title=title,
                        sticky=False
                    )
                except:
                    pass
            
            return notification
        except Exception as e:
            _logger.error(f"Error creating partner notification: {e}")
            return False

    @api.model
    def create_stage_change_notification(self, lead, old_stage, new_stage):
        """Create notification for stage change"""
        if not lead or not lead.user_id:
            return False
            
        title = _("Lead Stage Changed")
        message = _("Lead '%s' stage changed from '%s' to '%s'") % (
            lead.name,
            old_stage.name if old_stage else 'None',
            new_stage.name if new_stage else 'None'
        )
        
        try:
            notification = self.sudo().create({
                'title': title,
                'message': message,
                'lead_id': lead.id,
                'user_id': lead.user_id.id,
                'notification_type': 'stage_change',
                'is_read': False
            })
            
            # Send popup notification
            if lead.user_id.partner_id:
                try:
                    lead.user_id.notify_info(
                        message=message,
                        title=title,
                        sticky=False
                    )
                except:
                    pass
            
            return notification
        except Exception as e:
            _logger.error(f"Error creating stage change notification: {e}")
            return False