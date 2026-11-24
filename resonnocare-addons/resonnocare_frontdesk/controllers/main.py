from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, MissingError
import logging

_logger = logging.getLogger(__name__)

class DiscountApprovalController(http.Controller):

    def _get_record_and_validate(self, record_id, token):
        """Helper to fetch record and validate token."""
        record = request.env['resonnocare.discount.approval.request'].sudo().browse(record_id)
        
        if not record.exists():
            raise MissingError("The requested record does not exist.")
        
        # Validate token
        if not token or record.access_token != token:
            raise AccessError("Invalid or missing security token.")
            
        return record

    @http.route('/discount/approve/<int:record_id>', type='http', auth='user', website=True, csrf=False)
    def approve_discount(self, record_id, token=None, **kw):
        try:
            record = self._get_record_and_validate(record_id, token)
            
            if record.state != 'approved':
                record.with_user(request.env.user).action_approve()
            
            # Redirect to the exact URL format you provided
            # Format: /{app_name}/action-{action_id}/{record_id}
            return request.redirect(f'/resonnocare/action-928/{record.id}')
                
        except AccessError as e:
            return request.render('your_module_name.error_403_template', {'message': str(e)})
        except MissingError as e:
            return request.render('your_module_name.error_404_template', {'message': str(e)})
        except Exception as e:
            _logger.error("Approval Error: %s", str(e))
            return request.render('your_module_name.error_500_template', {'message': "An unexpected error occurred."})

    @http.route('/discount/reject/<int:record_id>', type='http', auth='user', website=True, csrf=False)
    def reject_discount(self, record_id, token=None, **kw):
        try:
            record = self._get_record_and_validate(record_id, token)
            
            if record.state != 'rejected':
                record.with_user(request.env.user).action_reject()
            
            # Redirect to the exact URL format you provided
            return request.redirect(f'/resonnocare/action-928/{record.id}')
                
        except AccessError as e:
            return request.render('your_module_name.error_403_template', {'message': str(e)})
        except MissingError as e:
            return request.render('your_module_name.error_404_template', {'message': str(e)})
        except Exception as e:
            _logger.error("Rejection Error: %s", str(e))
            return request.render('your_module_name.error_500_template', {'message': "An unexpected error occurred."})